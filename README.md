# jageocoder-server

このプログラムは、日本語住所ジオコーダー jageocoder を利用して
住所文字列を解析したり CSV に含まれる住所表記に経緯度を追加するといった
処理を実現するウェブアプリケーションです。

データファイルをダウンロードしておけば、スタンドアロンで動作します。
ネットワークが利用できない災害時、セキュリティ上の理由で外部サービスを
利用できない環境、または外部に送信できないデータをローカル環境で
処理したい場合などに利用できます。

また、サブネット内で他のアプリケーションから利用できる WebAPI 
サーバ機能も提供します。

# 利用手順

- [GitHub](https://github.com/t-sagara/jageocoder-server) から
    最新のコードを clone, または ZIP ファイルをダウンロードしてください。
- 任意の場所に展開し、ターミナル (Windows の場合は PowerShell) で
    この README.md ファイルがあるディレクトリを開いてください。

## Docker を利用する場合

- [Docker Engine](https://docs.docker.com/engine/) または
    [Docker Desktop](https://www.docker.com/products/docker-desktop/) が必要です。

- インストールする辞書をセットします。

    - [データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/)
        からダウンロードし、`data/` に配置してください。

    - data ディレクトリの zip ファイルの中で、更新日時が最も新しいものがインストールされます。

- サーバ設定の設定を確認します。

    `server/secret/env.dist` を `server/secret/.env` にコピーしてください。
    `server/secret/.env` で環境変数を設定することで、サーバの設定を行うことができます。
    
    **注意** このファイルを変更した場合は、次の `docker compose build` を実行して、変更内容をコンテナ内に反映してください。

    - `SITE_MESSAGE`: サーバに表示する文字列を設定できます。

    - `GEOCODING_REQUEST_PARAMS_*`: WebAPI ページの住所ジオコーディングAPIのリクエストパラメータを設定できます。

    - `RGEOCODING_REQUEST_PARAMS_*`: WebAPI ページのリバース住所ジオコーディングAPIのリクエストパラメータを設定できます。

    - `LAN_MODE`: 1 にすると、地図表示のために地理院地図サーバに
        アクセスするといった外部ネットワークへの通信を行いません。

    - `BUILD_RTREE`: 1 にすると、リバースジオコーディング機能に
        必要なインデックスを初回起動時に構築します。

- 以下の手順でコンテナを作成し、実行します。

        $ docker compose build
        $ docker compose up -d

    初回起動時、または新しい辞書ファイルが配置された場合には、
    自動的に辞書のインストールを行います。

    所要時間は辞書のサイズやコンピュータの性能にもよりますが、
    たとえば全国の住居表示レベルの場合は 1 分間程度かかります。

    `BUILD_RTREE` を 1 にした場合、リバースジオコーディング用の
    R-tree インデックスも構築します。こちらは 10 分間以上かかります。

    `data/init.log` に進捗状況が出力されますので、
    `Starting server process...` と表示されるまでのんびりお待ちください。

- ブラウザで `http://localhost:5000/` にアクセスしてご利用ください。

- 作業が終わったらコンテナを停止します。

        $ docker compose down

    インストールした辞書データは Docker Volume に保存されているので、
    二回目以降の実行時はコンテナを起動すればすぐに利用できます。

        $ docker compose up -d

- 辞書を更新するには、 `data/` に新しい辞書ファイルを置いてから、
  コンテナを再起動してください。
  
        $ docker compose down
        $ docker compose up -d

- もう利用しない場合はアンインストールしてください。

    完全にアンインストールするには `-v` オプションを指定して
    辞書がインストールされている Volume も削除します。

        $ docker compose down -v
        $ docker system prune

## Linux の場合

- Python3.8 以上がインストールされている環境が必要です。

    他の Python アプリケーションとの競合を防ぐため、
    `venv` 等で仮想環境を作成することをお勧めします。

        $ python -m venv .venv
        $ .venv/bin/activate

- Python パッケージをインストールします。

        $ python -m pip install -r requrements.txt

- 辞書データファイルをダウンロード・インストールします。

    サーバ上の他のアプリケーションで辞書データをインストール済みの場合、
    辞書がインストールされているディレクトリを環境変数 `JAGEOCODER_DB2_DIR` に
    セットしてください。

    インストールされていない場合や新しい辞書に更新したい場合は
    [データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/)
    から適切なデータファイルをダウンロードして、次のコマンドでインストールしてください。

        $ jageocoder install-dictionary <データファイルzip>
        (例)
        $ jageocoder install-dictionary jukyo_all_v20.zip

    リバースジオコーディング機能を利用したい場合は、
    R-tree インデックスを構築しておく必要があります。
    以下のコマンドを実行してインデックスを構築してください。

        $ jageocoder reverse 140.0 35.0

    サーバを起動中に R-tree インデックスを構築した場合、
    一度サーバを Ctrl+C で停止して、再度起動してください。

- サーバ設定の設定を確認します。

    `server/secret/env.dist` を `server/secret/.env` にコピーしてください。

    `server/secret/.env` で環境変数を設定することで、サーバの設定を行うことができます。

    - `SITE_MESSAGE`: サーバに表示する文字列を設定できます。

    - `GEOCODING_REQUEST_PARAMS_*`: WebAPI ページの住所ジオコーディングAPIのリクエストパラメータを設定できます。

    - `RGEOCODING_REQUEST_PARAMS_*`: WebAPI ページのリバース住所ジオコーディングAPIのリクエストパラメータを設定できます。

    - `LAN_MODE`: 1 にすると、地図表示のために地理院地図サーバに
        アクセスするといった外部ネットワークへの通信を行いません。

    - `BUILD_RTREE`: 1 にすると、リバースジオコーディング機能に
        必要なインデックスを初回起動時に構築します。

- サーバを起動します。

        $ python server/run_waitress.py

    サーバのバインドアドレス (0.0.0.0) やポート (5000) を変更したい場合は
    環境変数 `JAGEOCODER_SERVER_HOST` および `JAGEOCODER_SERVER_PORT` を
    指定して実行してください。

        $ JAGEOCODER_SERVER_PORT=8000 python server/run_waitress.py

- ブラウザで `http://<server>:5000/` にアクセスしてください。

    ポートを変更した場合はそのポート番号を指定してください。

- 作業が終わったらサーバを停止します。

    実行中のプロセスを Ctrl+C で終了します。

## 著作者表示

* **相良 毅** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## ライセンス

* このプログラムは [the MIT License](https://opensource.org/licenses/mit-license.php)
  に従って自由にインストール・利用が可能です。

* ただし住所データベースについては、データ提供元による利用条件があります。

## 関連情報

* ジオコーダー jageocoder および住所データベースについては
  https://t-sagara.github.io/jageocoder/ を参照してください。
