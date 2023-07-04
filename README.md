# jageocoder-server

このプログラムは、日本語住所ジオコーダー jageocoder を利用して
住所文字列を解析したり CSV に含まれる住所表記に経緯度を追加するといった
処理を実現するウェブアプリケーションです。

あらかじめデータファイルをダウンロードしておけば、スタンドアロンで動作します。
災害時やセキュリティ上の理由で外部サービスを利用できない環境や、
外部に送信できないデータをローカル環境で処理することができます。

また、サブネット内で他のアプリケーションから利用できる WebAPI も提供します。

# 利用手順

## Docker を利用する場合

- [Docker Engine](https://docs.docker.com/engine/) または
  [Docker Desktop](https://www.docker.com/products/docker-desktop/) が必要です。

- インストールする辞書をセットします。

    - [データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/)
      からダウンロードし、`data/` に配置してください。
    - zip ファイル名を `docker-compose.yml` の `DICFILE` で
      指定してください。

- 以下の手順でコンテナを作成し、実行します。

        $ docker compose build
        $ docker compose up -d

    初回インストール時には、辞書のインストールとリバースジオコーディング用の
    R-tree インデックスを構築します。

    所要時間は辞書のサイズやコンピュータの性能にもよりますが、
    たとえば全国の住居表示レベルの場合は 10 分間以上かかります。
    `data/init.log` に進捗状況が出力されますので、 `All done.` と
    表示されるまでのんびりお待ちください。

- ブラウザで `http://localhost:5000/` にアクセスしてご利用ください。

- 作業が終わったらコンテナを停止します。

        $ docker compose down

    インストールした辞書データは Docker Volume に保存されているので、
    二回目以降の実行時はコンテナを起動すればすぐに利用できます。

        $ docker compose up -d

- もう利用しない場合はアンインストールしてください。

    完全にアンインストールするには Volume も削除してください。

        $ docker compose down -v
        $ docker system prune

## Linux の場合

- Python3.7 以上がインストールされている環境が必要です。

    他の Python アプリケーションとの競合を防ぐため、
    `venv` 等で仮想環境を作成することをお勧めします。

        $ python -m venv .venv
        $ .venv/bin/activate

- 以下の手順で実行に必要なパッケージおよびデータをインストールします。

        $ python -m pip install -r requrements.txt
        $ curl https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v20.zip -o data/jukyo_all_v20.zip
        $ python -m jageocoder install-dictionary data/jukyo_all_v20.zip

- サーバを起動します。

        $ cd server
        $ gunicorn app:app --bind='0.0.0.0:5000'

- ブラウザで `http://<server>:5000/` にアクセスしてください。

- 作業が終わったらサーバを停止します。

    実行中のプロセスを Ctrl+C で終了します。

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
