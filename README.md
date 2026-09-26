E:\distrinet-cic-ids\
│
├── .venv\
│
├── data\

│   └── raw\
│       ├── Benign-Monday.parquet

│       ├── Bruteforce-Tuesday.parquet

│       ├── DoS-Wednesday.parquet

│       ├── Infiltration-Webattacks-Thursday.parquet

│       └── Portscan-DDoS-Botnet-Friday.parquet
│
├── notebooks\

├── src\

├── app\

└── artifacts\

Bước 1:mở cmd

E:

cd \

mkdir distrinet-cic-ids

cd distrinet-cic-ids


mkdir data

mkdir data\raw

mkdir notebooks

mkdir src

mkdir app

mkdir artifacts

dir


Bước 2: Kiểm tra Python và kích hoạt môi trường:

python --version (hoặc py --version)

python -m venv .venv (hoặc py -m venv .venv)

.venv\Scripts\activate (hiện như này là thành công: (.venv) E:\distrinet-cic-ids> )


Bước 3: Cài Kaggle và thư viện

python -m pip install --upgrade pip

pip install kaggle pandas pyarrow scikit-learn

kaggle --version

$env:KAGGLE_API_TOKEN="KGAT_xxx" (với xxx là API token của kaggle)

kaggle datasets list -s distrinetcicids2017 (hiện như này là thành công: dhoogla/distrinetcicids2017)

kaggle datasets download -d dhoogla/distrinetcicids2017 -p E:\distrinet-cic-ids\data\raw --unzip

dir E:\distrinet-cic-ids\data\raw


Bước 4: Tạo file: E:\distrinet-cic-ids\src\check_dataset.py

Và Chạy file: python src\check_dataset.py


Bước 5: Tạo file: E:\distrinet-cic-ids\src\prepare_data.py

Và Chạy file: python src\prepare_data.py
