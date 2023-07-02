# jageocoder-server

このプログラムは、日本語住所ジオコーダー jageocoder を利用して
CSV に含まれる住所表記に経緯度を追加したり、住所文字列を解析する
ウェブアプリケーションです。

外部サービスを利用できない環境や、外部に送信できないデータを
ローカル環境で処理することができます。

また、他のアプリケーションから利用できる WebAPI も提供します。

# 利用手順

## Linux の場合

- Python3.7 以上がインストールされている環境が必要です。

    他の Python アプリケーションとの競合を防ぐため、
    venv 等で仮想環境を作成することをお勧めします。

        $ python -m venv .venv
        $ .venv/bin/activate

- 以下の手順で実行に必要なパッケージおよびデータをインストールします。

        $ python -m pip install -r requrements.txt
        $ curl https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v20.zip -o jukyo_all_v20.zip
        $ python -m jageocoder install-dictionary jukyo_all_v20.zip

- サーバを起動します。

        $ cd server
        $ gunicorn app:app --bind='0.0.0.0:5000'

- ブラウザで `http://<server>:5000/` にアクセスしてください。

- 作業が終わったらサーバを停止します。

    実行中のプロセスを Ctrl+C で終了します。

## Docker を利用する場合

- Docker Server または Docker Desktop が必要です。

- 以下の手順でコンテナを作成して実行します。

        $ docker compose build
        $ docker compose up -d

- ブラウザで `http://localhost:5000/` にアクセスしてください。

- 作業が終わったらコンテナを停止します。

        $ docker compose down


## 著作者表示

* **相良 毅** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## ライセンス

このプログラムは [the MIT License](https://opensource.org/licenses/mit-license.php)
に従って自由にインストール・利用が可能です。

ただし住所データベースについては、データ提供元による利用条件があります。

## 関連情報

ジオコーダー jageocoder および住所データベースについては
https://t-sagara.github.io/jageocoder/
から参照してください。
