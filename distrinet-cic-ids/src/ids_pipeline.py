"""Cac bo phan tien xu ly dung chung cho huan luyen VA ung dung.
Moi bo phan co .fit() (hoc tu TRAIN) va .transform() (chi ap dung, khong hoc lai).
Moi bo phan ghi lai n_fit_rows_ = so dong da dung de hoc, de kiem chung chi hoc tren train."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42


def _df(X):
    return X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)


class DropConstant(BaseEstimator, TransformerMixin):
    """Bo cot chi co 1 gia tri duy nhat TREN TRAIN."""
    def fit(self, X, y=None):
        X = _df(X)
        self.n_fit_rows_ = len(X)
        self.dropped_ = [c for c in X.columns if X[c].nunique(dropna=False) <= 1]
        self.keep_ = [c for c in X.columns if c not in self.dropped_]
        return self

    def transform(self, X):
        return _df(X)[self.keep_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.keep_, dtype=object)


class SignedLog1p(BaseEstimator, TransformerMixin):
    """sign(x)*log(1+|x|): ham CO DINH, khong hoc gi tu du lieu.
    Giam do lech cua cac cot co gia tri rat lon (byte/s, thoi gian...)."""
    def fit(self, X, y=None):
        self.n_fit_rows_ = len(X)
        self.cols_ = list(_df(X).columns)
        return self

    def transform(self, X):
        X = _df(X)
        v = X.to_numpy(dtype="float64")
        return pd.DataFrame(np.sign(v) * np.log1p(np.abs(v)), columns=X.columns, index=X.index)

    def get_feature_names_out(self, input_features=None):
        return np.array(self.cols_, dtype=object)


class CorrelationFilter(BaseEstimator, TransformerMixin):
    """Trong moi cap cot tuong quan |r| > threshold (tinh TREN TRAIN), bo cot dung sau."""
    def __init__(self, threshold=0.95, sample=300_000, random_state=SEED):
        self.threshold, self.sample, self.random_state = threshold, sample, random_state

    def fit(self, X, y=None):
        X = _df(X)
        self.n_fit_rows_ = len(X)
        S = X.sample(n=min(self.sample, len(X)), random_state=self.random_state)
        corr = S.astype("float64").corr().abs().fillna(0).to_numpy()
        cols = list(X.columns)
        drop = set()
        for i in range(len(cols)):
            if cols[i] in drop:
                continue
            for j in range(i + 1, len(cols)):
                if cols[j] not in drop and corr[i, j] > self.threshold:
                    drop.add(cols[j])
        self.dropped_ = [c for c in cols if c in drop]
        self.keep_ = [c for c in cols if c not in drop]
        return self

    def transform(self, X):
        return _df(X)[self.keep_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.keep_, dtype=object)


class TopKSelector(BaseEstimator, TransformerMixin):
    """Chon k dac trung quan trong nhat theo Random Forest hoc TREN TRAIN
    (dung mau con phan tang cua train de nhanh)."""
    def __init__(self, k=30, sample=300_000, random_state=SEED):
        self.k, self.sample, self.random_state = k, sample, random_state

    def fit(self, X, y):
        X = _df(X)
        y = np.asarray(y)
        self.n_fit_rows_ = len(X)
        rng = np.random.default_rng(self.random_state)
        idx = np.arange(len(X))
        if len(X) > self.sample:
            idx = np.concatenate([
                rng.choice(np.where(y == c)[0],
                           size=max(1, int(round(self.sample * (y == c).mean()))), replace=False)
                for c in np.unique(y)])
        rf = RandomForestClassifier(n_estimators=100, n_jobs=-1, class_weight="balanced",
                                    random_state=self.random_state, min_samples_leaf=2)
        rf.fit(X.iloc[idx], y[idx])
        self.importances_ = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
        self.keep_ = list(self.importances_.index[: min(self.k, X.shape[1])])
        return self

    def transform(self, X):
        return _df(X)[self.keep_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.keep_, dtype=object)


class ProtocolEncoder(BaseEstimator, TransformerMixin):
    """One-hot cot Protocol (6=TCP, 17=UDP, 0=khac). Danh sach gia tri hoc TREN TRAIN;
    gia tri la xuat hien sau nay -> tat ca cot one-hot = 0 (khong bao loi)."""
    def __init__(self, column="Protocol"):
        self.column = column

    def fit(self, X, y=None):
        X = _df(X)
        self.n_fit_rows_ = len(X)
        self.ohe_ = OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype="float64")
        self.ohe_.fit(X[[self.column]])
        self.ohe_cols_ = [f"{self.column}_{v}" for v in self.ohe_.categories_[0]]
        self.other_ = [c for c in X.columns if c != self.column]
        return self

    def transform(self, X):
        X = _df(X)
        oh = pd.DataFrame(self.ohe_.transform(X[[self.column]]), columns=self.ohe_cols_, index=X.index)
        return pd.concat([oh, X[self.other_]], axis=1)

    def get_feature_names_out(self, input_features=None):
        return np.array(self.ohe_cols_ + self.other_, dtype=object)


def build_preprocess(k=30, corr_threshold=0.95):
    """Day chuyen tien xu ly: ma hoa Protocol -> bo cot hang -> log -> loc tuong quan
    -> chuan hoa -> chon k dac trung."""
    pipe = Pipeline([
        ("encoder", ProtocolEncoder()),
        ("drop_constant", DropConstant()),
        ("log", SignedLog1p()),
        ("corr_filter", CorrelationFilter(threshold=corr_threshold)),
        ("scaler", StandardScaler()),
        ("select", TopKSelector(k=k)),
    ])
    pipe.set_output(transform="pandas")
    return pipe


def fit_row_counts(pipe):
    """Tra ve so dong ma tung bo phan da dung de hoc (de kiem chung chi hoc tren train)."""
    out = {}
    for name, step in pipe.steps:
        n = getattr(step, "n_fit_rows_", None)
        if n is None:
            n = getattr(step, "n_samples_seen_", None)
        out[name] = None if n is None else int(np.max(n))
    return out
