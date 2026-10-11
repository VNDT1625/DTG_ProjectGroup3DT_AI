"""Bước 13 (cập nhật) — Stratified 70/15/15 trước, RF Temporal CV trong Train.

Chạy từ thư mục có main.py, step6_temporal_split_first.py và data/raw/:
    python step13_stratified_then_temporal_cv_updated.py --jobs 4

Tùy chọn (chỉ sau khi khóa lựa chọn mô hình, và phải báo cáo rằng test từng được xem):
    python step13_stratified_then_temporal_cv_updated.py --jobs 4 --evaluate-test

Quan trọng: Temporal CV bên trong train *không biến* random test thành temporal test.
Vì các test đã từng được xem trong giai đoạn thăm dò, mọi kết quả test mới
cũng chỉ mang tính thăm dò. Cần dữ liệu mới để có external test độc lập.
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.exceptions import ConvergenceWarning

from main import SEED, build_models, get_metrics, read_parquets, normalized
from step6_temporal_split_first import (
    best_threshold,
    clean_train_only,
    hash_features,
    prepare_without_global_dedup,
)

# Hai cấu hình RF để lựa chọn chỉ bằng temporal CV (không dùng test).
LR_MAX_ITER = 2000  # tăng giới hạn; không bỏ qua ConvergenceWarning

RF_CANDIDATES = {
    "rf_baseline": {"n_estimators": 120, "max_depth": 18, "min_samples_leaf": 3},
    "rf_shallower": {"n_estimators": 100, "max_depth": 12, "min_samples_leaf": 5},
}


def stratified_split_first(df: pd.DataFrame):
    """Phân tầng 70/15/15 trước khi loại dữ liệu trùng theo X hoặc nhãn mâu thuẫn."""
    indices = df.index.to_numpy()
    train_idx, other_idx = train_test_split(
        indices, test_size=0.30, stratify=df["__target"], random_state=SEED
    )
    val_idx, test_idx = train_test_split(
        other_idx,
        test_size=0.50,
        stratify=df.loc[other_idx, "__target"],
        random_state=SEED,
    )
    return (df.loc[train_idx].copy(), df.loc[val_idx].copy(), df.loc[test_idx].copy())


def strict_eval_view(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    features: list[str],
    additional_prior: pd.DataFrame | None = None,
):
    """Không dùng nhãn val/test để xóa/lựa chọn bản ghi. Chỉ dùng vector X.

    Loại mọi nhóm feature bị trùng nội bộ để tránh chọn tùy ý một nhãn bất nhất.
    Chỉ dùng X của tập đánh giá để quyết định có đưa bản ghi vào giao thức 'strict'.
    """
    prior = set(hash_features(train, features).to_numpy().tolist())
    if additional_prior is not None:
        prior.update(hash_features(additional_prior, features).to_numpy().tolist())
    fp = hash_features(eval_frame, features)
    overlap = fp.isin(prior)
    repeats = fp.duplicated(keep=False)
    kept = eval_frame.loc[~(overlap | repeats)].copy()
    audit = {
        "original": int(len(eval_frame)),
        "overlap_with_prior": int(overlap.sum()),
        "repeated_X_rows_within_split": int(repeats.sum()),
        "strict_kept": int(len(kept)),
    }
    return kept, audit


def check_data(frame: pd.DataFrame, name: str):
    counts = frame["__target"].value_counts().to_dict()
    print(
        f"  {name}: {len(frame):,} rows; "
        f"attack={frame['__target'].mean():.2%}" if len(frame) else f"  {name}: EMPTY"
    )
    if set(counts) != {0, 1}:
        raise ValueError(f"{name} thiếu một lớp nhãn: {counts}")


def _probability_diagnostics(y_true, probs: np.ndarray) -> dict:
    """Mô tả điểm dự đoán; KHÔNG dùng để chọn ngưỡng mới cho từng fold."""
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probs, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("RF trả về probability không hữu hạn")
    result = {
        "predicted_attack_rate_at_05": float(np.mean(p >= 0.5)),
    }
    for label, title in [(0, "benign"), (1, "attack")]:
        part = p[y == label]
        result[f"score_{title}_q10"] = float(np.quantile(part, 0.10))
        result[f"score_{title}_median"] = float(np.median(part))
        result[f"score_{title}_q90"] = float(np.quantile(part, 0.90))
        result[f"score_{title}_q99"] = float(np.quantile(part, 0.99))
    return result


def _attack_label_audit(past_raw: pd.DataFrame, future_raw: pd.DataFrame, day: int):
    """Chỉ phân tích nhãn gốc theo từng ngày, không dùng để tối ưu model."""
    label_columns = [
        c for c in past_raw.columns if normalized(c) in {"label", "attacklabel"}
    ]
    if len(label_columns) != 1:
        return [], None
    column = label_columns[0]
    seen = set(past_raw.loc[past_raw["__target"] == 1, column].astype(str).str.strip().str.casefold())
    future_attacks = future_raw.loc[future_raw["__target"] == 1, column].astype(str).str.strip()
    label_rows = []
    for label, n in future_attacks.value_counts().items():
        unknown = label.casefold() not in seen
        label_rows.append({
            "validation_day": day,
            "attack_label": label,
            "rows": int(n),
            "unseen_attack_type_in_fold_train": bool(unknown),
        })
    unseen_rows = sum(item["rows"] for item in label_rows if item["unseen_attack_type_in_fold_train"])
    return label_rows, (unseen_rows / len(future_attacks) if len(future_attacks) else None)


def temporal_cv_choose_rf(train_raw: pd.DataFrame, features: list[str], jobs: int):
    """Mon–Tue -> Wed, Mon–Wed -> Thu, Mon–Thu -> Fri trong phần TRAIN 70%.

    Mỗi fold chỉ fit trên ngày quá khứ. Kết quả trên ngày kế tiếp là chẩn đoán
    ở NGƯỠNG CỐ ĐỊNH 0.5; không tự điều chỉnh threshold bằng nhãn fold val.
    """
    if not train_raw["__capture_day"].notna().all():
        raise ValueError("Không xác định được ngày trong tên file: không thể temporal CV")
    days = set(train_raw["__capture_day"].astype(int).unique().tolist())
    if not {0, 1, 2, 3, 4}.issubset(days):
        raise ValueError(f"Không đủ 5 ngày phục vụ temporal CV: {sorted(days)}")

    results = []
    attack_type_rows = []
    for target_day in [2, 3, 4]:
        raw_past = train_raw.loc[train_raw["__capture_day"] < target_day]
        raw_future = train_raw.loc[train_raw["__capture_day"] == target_day]
        past, _ = clean_train_only(raw_past, features)
        next_day, overlap_audit = strict_eval_view(past, raw_future, features)
        check_data(past, f"Fold TRAIN days < {target_day}")
        check_data(next_day, f"Fold VALID day = {target_day}")
        print(
            f"  Temporal fold day={target_day} | train={len(past):,}, "
            f"validation={len(next_day):,} | val excluded={overlap_audit['original']-len(next_day):,}"
        )
        label_rows, unseen_fraction = _attack_label_audit(raw_past, next_day, target_day)
        attack_type_rows.extend(label_rows)
        if unseen_fraction is not None:
            print(f"  Attack thuộc nhãn CHƯA CÓ trong fold train: {unseen_fraction:.2%} (theo tên nhãn gốc)")
        for name, rf_params in RF_CANDIDATES.items():
            model = build_models(jobs, past["__target"])["RandomForest"]
            model.set_params(**{f"classifier__{k}": v for k, v in rf_params.items()})
            model.fit(past[features], past["__target"])
            probs = model.predict_proba(next_day[features])[:, 1]
            score = get_metrics(next_day["__target"], (probs >= 0.5).astype(int), probs)
            diagnostics = _probability_diagnostics(next_day["__target"], probs)
            base_rate = float(next_day["__target"].mean())
            lift = float(score["pr_auc"] / base_rate) if base_rate > 0 else float("nan")
            print(
                f"    {name}: AP={score['pr_auc']:.4f} | AP random~{base_rate:.4f} "
                f"| AP lift={lift:.2f} | ROC={score['roc_auc']:.4f} | "
                f"P={score['precision']:.4f} R={score['recall']:.4f} "
                f"F1@0.5={score['f1']:.4f} | FP={score['fp']:,} FN={score['fn']:,}"
            )
            print(
                f"      score median: BENIGN={diagnostics['score_benign_median']:.5g}; "
                f"ATTACK={diagnostics['score_attack_median']:.5g}; "
                f"% dự đoán ATTACK @0.5={diagnostics['predicted_attack_rate_at_05']:.2%}"
            )
            results.append({
                "fold_validation_day": int(target_day),
                "fold_train_rows": int(len(past)),
                "fold_validation_rows": int(len(next_day)),
                "fold_validation_attack_rate": base_rate,
                "pr_auc_random_reference": base_rate,
                "pr_auc_lift_over_random": lift,
                "fraction_attacks_with_unseen_label": unseen_fraction,
                "excluded_validation_rows_by_X": overlap_audit['original'] - len(next_day),
                "candidate": name,
                "rf_params": json.dumps(rf_params),
                **score,
                **diagnostics,
            })
            del model

    cv_table = pd.DataFrame(results)
    rank = (
        cv_table.groupby("candidate", as_index=False)
        .agg(
            mean_pr_auc=("pr_auc", "mean"),
            mean_ap_lift=("pr_auc_lift_over_random", "mean"),
            mean_f1_at_05=("f1", "mean"),
            min_fold_pr_auc=("pr_auc", "min"),
        )
        .sort_values(["mean_pr_auc", "mean_f1_at_05"], ascending=False)
    )
    winner = str(rank.iloc[0]["candidate"])
    print("\nTemporal CV trong Train 70% (vẫn xếp hạng theo TRUNG BÌNH AP/PR-AUC):")
    print(rank.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"=> RF được chọn TRƯỚC khi xem validation 15%: {winner}")
    print("  Cảnh báo: tỉ lệ ATTACK và loại tấn công thay đổi theo ngày; điểm trung bình che khuất fold khó.")
    return winner, cv_table, rank, pd.DataFrame(attack_type_rows)


def fit_and_evaluate(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame | None,
    features: list[str],
    rf_winner: str,
    jobs: int,
    out_dir: Path,
    evaluate_test: bool,
):
    models = build_models(jobs, train["__target"])
    # main.py đã có StandardScaler trong pipeline LR; chỉ tăng số vòng lặp.
    models["LogisticRegression"].set_params(classifier__max_iter=LR_MAX_ITER)
    models["RandomForest"].set_params(
        **{f"classifier__{key}": value for key, value in RF_CANDIDATES[rf_winner].items()}
    )
    metrics = []
    fitted = {}
    choices = {}
    for name, pipeline in models.items():
        print(f"\nHuấn luyện {name} trên TOÀN BỘ Train 70% sau làm sạch")
        if name == "LogisticRegression":
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always", ConvergenceWarning)
                pipeline.fit(train[features], train["__target"])
            convergence_warnings = [w for w in records if issubclass(w.category, ConvergenceWarning)]
            cls = pipeline.named_steps["classifier"]
            steps_used = int(np.max(cls.n_iter_))
            print(f"  Logistic Regression: max_iter={cls.max_iter}, n_iter_={steps_used}")
            if convergence_warnings:
                print("  CẢNH BÁO: LR vẫn chưa hội tụ; kết quả cần chú thích trong báo cáo.")
                print(f"  {str(convergence_warnings[0].message).splitlines()[0]}")
            elif steps_used >= cls.max_iter:
                print("  Chú ý: LR chạm max_iter; hãy kiểm tra tình trạng hội tụ.")
            else:
                print("  Không xuất hiện ConvergenceWarning ở lần fit này.")
        else:
            pipeline.fit(train[features], train["__target"])
        probs = pipeline.predict_proba(validation[features])[:, 1]
        thr = best_threshold(validation["__target"].to_numpy(), probs)
        base = get_metrics(validation["__target"], (probs >= 0.5).astype(int), probs)
        tuned = get_metrics(validation["__target"], (probs >= thr).astype(int), probs)
        metrics.extend([
            {"model": name, "setting": "default_05", "threshold": 0.5, **base},
            {"model": name, "setting": "tuned_on_same_validation", "threshold": thr, **tuned},
        ])
        print(
            f"  Validation: PR-AUC={base['pr_auc']:.4f} | "
            f"F1@0.5={base['f1']:.4f} | F1@tuned={tuned['f1']:.4f} | threshold={thr:.8g}"
        )
        fitted[name] = pipeline
        choices[name] = {"threshold": float(thr), "val_f1_tuned": float(tuned["f1"]),
                         "val_pr_auc": float(tuned["pr_auc"])}
        joblib.dump(pipeline, out_dir / f"{name}.joblib", compress=3)
    pd.DataFrame(metrics).to_csv(out_dir / "validation_metrics.csv", index=False)

    # Có thể chọn RF vì nội bộ temporal CV; nếu muốn chọn 'best overall', dựa vào validation15.
    best_validation = max(choices, key=lambda n: (choices[n]["val_f1_tuned"], choices[n]["val_pr_auc"]))
    print(f"\nMô hình F1 tốt nhất trên validation 15%: {best_validation}")
    print("RF đã chọn cấu hình qua Temporal CV. XGBoost vẫn là mô hình nghiên cứu chính.")

    if evaluate_test:
        assert test is not None, "Phải chuẩn bị dữ liệu test khi --evaluate-test"
        print("\nCẢNH BÁO: Dữ liệu test từng được sử dụng ở các thử nghiệm trước của dự án.")
        print("Không mô tả kết quả này là đánh giá cuối hoàn toàn độc lập!")
        rows = []
        for name, pipeline in fitted.items():
            pr = pipeline.predict_proba(test[features])[:, 1]
            thr = choices[name]["threshold"]
            m = get_metrics(test["__target"], (pr >= thr).astype(int), pr)
            rows.append({"model": name, "threshold_selected_on_validation": thr, **m})
            print(f"  Test (exploratory) {name}: F1={m['f1']:.4f} | Recall={m['recall']:.4f} | FP={m['fp']:,} FN={m['fn']:,}")
        pd.DataFrame(rows).to_csv(out_dir / "exploratory_test_metrics.csv", index=False)
    else:
        print("\nChưa dự đoán hoặc kiểm toán Test. Muốn đánh giá cần thêm --evaluate-test; test từng được xem trong các bước trước.")
    return choices, best_validation


def run(args):
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    raw = read_parquets(args.data_dir)
    df, features = prepare_without_global_dedup(raw)
    del raw
    print("\n=== BƯỚC 1: STRATIFIED SPLIT 70/15/15 (TRƯỚC DEDUP) ===")
    tr_raw, va_raw, te_raw = stratified_split_first(df)
    for name, part in [("Train 70% (raw)", tr_raw), ("Validation 15% (raw)", va_raw)]:
        check_data(part, name)
    print(f"  Test 15% (raw): {len(te_raw):,} dòng; được giữ riêng, chưa sử dụng để chọn mô hình")
    del df

    print("\n=== BƯỚC 2: TEMPORAL CV CHỈ BÊN TRONG TRAIN 70% ===")
    winner, cv_table, cv_rank, attack_type_table = temporal_cv_choose_rf(tr_raw, features, args.jobs)
    cv_table.to_csv(out / "rf_temporal_cv_by_day.csv", index=False)
    cv_rank.to_csv(out / "rf_temporal_cv_ranking.csv", index=False)
    attack_type_table.to_csv(out / "rf_temporal_cv_attack_types.csv", index=False)
    print("\nBẢNG CHẨN ĐOÁN RF THEO FOLD (ngưỡng 0.5; CHƯA tối ưu theo fold):")
    summary_cols = ["fold_validation_day", "candidate", "fold_validation_rows", "fold_validation_attack_rate", "pr_auc", "pr_auc_random_reference", "roc_auc", "precision", "recall", "f1", "fp", "fn"]
    print(cv_table[summary_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n=== BƯỚC 3: LÀM SẠCH TRAIN / KIỂM TRA TRÙNG GIỮA CÁC TẬP ===")
    train, train_audit = clean_train_only(tr_raw, features)
    val, val_audit = strict_eval_view(train, va_raw, features)
    test, test_audit = None, None
    print(f"validation feature-only duplicate audit: {val_audit}")
    for name, frame in [("Train (clean)", train), ("Validation (strict)", val)]:
        check_data(frame, name)
    if args.evaluate_test:
        # Chỉ tại đây mới mở nhánh xử lý test; không dùng test để chọn cấu hình.
        test, test_audit = strict_eval_view(train, te_raw, features, additional_prior=va_raw)
        print(f"test feature-only duplicate audit: {test_audit}")
        check_data(test, "Test (strict)")

    print("\n=== BƯỚC 4: FIT TRAIN VÀ ĐÁNH GIÁ VALIDATION ===")
    selections, best_model = fit_and_evaluate(
        train, val, test, features, winner, args.jobs, out, args.evaluate_test,
    )
    metadata = {
        "protocol": "stratified_70_15_15_then_temporal_cv_within_train70",
        "seed": SEED,
        "original_random_split": {"train": len(tr_raw), "validation": len(va_raw), "test": len(te_raw)},
        "after_feature_only_cross_partition_purging": {"train": len(train), "validation": len(val), "test": (len(test) if test is not None else None)},
        "note": "Phần trăm sau loại trùng có thể khác 70/15/15; chia ngẫu nhiên trước tiên vẫn đúng tỷ lệ.",
        "feature_columns": features,
        "rf_temporal_cv_selected": winner,
        "rf_temporal_cv_candidates": RF_CANDIDATES,
        "rf_temporal_cv_selection_criterion": "mean_pr_auc_from_fixed_future_day_folds",
        "rf_temporal_diagnostics_only_no_fold_threshold_tuning": True,
        "lr_max_iter": LR_MAX_ITER,
        "train_audit": train_audit,
        "validation_audit": val_audit,
        "test_audit": test_audit,
        "validation_threshold_choices": selections,
        "best_overall_val_f1": best_model,
        "test_was_previously_exposed_in_past_project_runs": True,
        "test_evaluated_in_this_run": bool(args.evaluate_test),
        "important_limit": "Temporal CV only within random 70% train; validation/test are random, not forward-in-time holdout.",
    }
    (out / "protocol_audit.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu kết quả trong: {out.resolve()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--output-dir", type=Path, default=Path("results/stratified_then_temporal_cv_diagnostics"))
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--evaluate-test", action="store_true", help="Mặc định KHÔNG dự đoán test. Chỉ bật sau khi khóa cấu hình.")
    run(p.parse_args())
