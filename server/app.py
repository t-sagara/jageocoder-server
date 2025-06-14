import copy
import csv
import jaconv
import json
from typing import List, Tuple
import os
from pathlib import Path
import re
import urllib
import uuid

import dotenv
from flask_cors import cross_origin
from flask import (
    Flask, flash, request, redirect, render_template,
    jsonify, Response, url_for, make_response)
from flask_jsonrpc.app import JSONRPC

import jageocoder
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode

jageocoder.init()
module_version = jageocoder.__version__
dictionary_version = jageocoder.installed_dictionary_version()
server_signature = str(uuid.uuid4())
tree = jageocoder.get_module_tree()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.json.ensure_ascii = False
jsonrpc = JSONRPC(app, "/jsonrpc", enable_web_browsable_api=False)

# Load environment variables from ".env", if exists.
envpath = Path(__file__).parent / 'secret/.env'
if envpath.exists:
    dotenv.load_dotenv(envpath)

tree_dir = Path(tree.db_dir)
if (tree_dir / "rtree.dat").exists() and \
        (tree_dir / "rtree.idx").exists():
    use_rgeocoder = True
else:
    use_rgeocoder = False

re_splitter = re.compile(r'[ \u2000,、]+')


@app.context_processor
def inject_versions():
    # Set globals in templates
    return {
        "module_version": module_version,
        "dictionary_version": dictionary_version,
        "SITE_MESSAGE": os.environ.get("SITE_MESSAGE"),
        "LAN_MODE": os.environ.get(
            "LAN_MODE", "0"),
    }


def _split_args(val: str) -> List[str]:
    args = re_splitter.split(val)
    args = [x for x in args if x != '']
    return args


def _extract_digits(val: str) -> str:
    """
    Converts numerical characters to ASCII and
    removes non-numeric characters.
    """
    hval = jaconv.z2h(val, kana=False, ascii=True, digit=True)
    return re.sub(r'[^\d\.]', '', hval)


@app.route("/")
def index():
    options = get_query_options(request)
    response = make_response(render_template(
        'index.html',
        **options,
        result=None
    ))
    return set_query_options(response, options)


@app.route("/azamaster/<code>", methods=['POST', 'GET'])
def get_aza(code):
    aza_node = tree.aza_masters.search_by_code(code)

    if aza_node:
        names = json.loads(aza_node.names)
    else:
        names = None

    return render_template(
        'aza.html',
        tree=tree,
        aza=aza_node, names=names)


@app.route("/searchby", methods=['POST', 'GET'])
def search_by():
    if request.method == 'POST':
        args = request.form
    else:
        args = request.args

    if args.get('postcode'):
        return redirect(url_for('search_postcode', code=args.get('postcode')))

    if args.get('citycode'):
        return redirect(url_for('search_jisx0402', code=args.get('citycode')))

    if args.get('prefcode'):
        return redirect(url_for('search_jisx0401', code=args.get('prefcode')))

    if args.get('aza_id'):
        return redirect(url_for('search_aza_id', aza_id=args.get('aza_id')))

    return redirect(url_for('index'))


@app.route("/reverse", methods=['POST', 'GET'])
def reverse():

    def _parse_degree(val: str) -> Tuple[float, str]:
        hval = jaconv.z2h(val)
        hval = re.sub(r'\s+', '', hval)

        # check deg, min, sec (ex. '35° 39′ 31″' or '35度39分31秒')
        m = re.search((
            r'(N|S|E|W|北緯|南緯|東経|西経|)(\-?\d+)[°度]'
            r'(\d+)[′分]([\d\.]+)[″秒]([NSEW]?)'), hval)
        if m:
            deg = float(m.group(2)) + float(m.group(3)) / 60.0\
                + float(m.group(4)) / 3600.0
            dir = ''
            if m.group(1) in ('N', '北緯') or m.group(5) == 'N':
                dir = 'lat'
            elif m.group(1) in ('S', '南緯') or m.group(5) == 'S':
                dir = 'lat'
                deg = -deg
            elif m.group(1) in ('E', '東経') or m.group(5) == 'E':
                dir = 'lon'
            elif m.group(1) in ('W', '西経') or m.group(5) == 'W':
                dir = 'lon'
                deg = -deg

            return (deg, dir)

        # check deg (ex. '35.658611')
        m = re.search((
            r'(N|S|E|W|北緯|南緯|東経|西経|)(\-?\d+)(\.\d+)?'
            r'[°度]?([NSEW]?)'), hval)
        if m:
            deg = float(m.group(2) + m.group(3) or '')
            dir = ''

            if m.group(1) in ('N', '北緯') or m.group(4) == 'N':
                dir = 'lat'
            elif m.group(1) in ('S', '南緯') or m.group(4) == 'S':
                dir = 'lat'
                deg = -deg
            elif m.group(1) in ('E', '東経') or m.group(4) == 'E':
                dir = 'lon'
            elif m.group(1) in ('W', '西経') or m.group(4) == 'W':
                dir = 'lon'
                deg = -deg

            return (deg, dir)

        return (None, '')

    if request.method == 'POST':
        args = request.form
    else:
        args = request.args

    if args.get('lat') and args.get('lon'):
        pass
    else:
        return redirect(url_for('index'))

    vlat = _parse_degree(args.get('lat'))
    vlon = _parse_degree(args.get('lon'))
    if vlat[1] == 'lon' or vlon[1] == 'lat':
        lon, lat = vlat[0], vlon[0]
    else:
        lon, lat = vlon[0], vlat[0]

    results = jageocoder.reverse(
        x=lon,
        y=lat,
        level=8,
        as_dict=False
    )

    if len(results) == 1:
        return redirect(url_for('show_node', id=results[0].node.id))

    nodes = [x["candidate"] for x in results]
    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/aza/<aza_id>", methods=['POST', 'GET'])
def search_aza_id(aza_id):
    aza_id = _extract_digits(aza_id)
    if len(aza_id) == 12:
        # jisx0402(5digits) + aza_id(7digits)
        candidates = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id[-7:])
        nodes = [x for x in candidates if x.get_city_jiscode() == aza_id[0:5]]
    elif len(aza_id) == 13:
        # lasdec(6digits) + aza_id(7digits)
        candidates = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id[-7:])
        nodes = [x for x in candidates
                 if x.get_city_local_authority_code() == aza_id[0:6]]
    else:
        nodes = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id)

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/jisx0401/<code>", methods=['POST', 'GET'])
def search_jisx0401(code):
    code = _extract_digits(code)

    if len(code) < 2:
        code = '0' + code

    nodes = tree.search_nodes_by_codes(
        category="jisx0401",
        value=code[0:2])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/jisx0402/<code>", methods=['POST', 'GET'])
def search_jisx0402(code):
    code = _extract_digits(code)

    while len(code) < 5:
        code = '0' + code

    nodes = tree.search_nodes_by_codes(
        category="jisx0402",
        value=code[0:5])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/postcode/<code>", methods=['POST', 'GET'])
def search_postcode(code):
    code = _extract_digits(code)
    nodes = tree.search_nodes_by_codes(
        category="postcode",
        value=code[0:7])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/csv", methods=['POST', 'GET'])
def csvmatch():
    import csvmatch
    input_args = {
        "head": "1", "ienc": "auto", "oenc": "auto",
        "ofname": "add_dt", "nc": "1",
    }
    for col in csvmatch.output_columns:
        if col[1][1] is True:
            input_args[col[0]] = "on"

    if request.method == 'GET':
        return render_template(
            'csv.html',
            columns=csvmatch.output_columns,
            args=input_args)

    try:
        input_args, chunk = csvmatch.parse_multipart_formdata()
        args = copy.copy(input_args)
        args, buf = csvmatch.check_params(args, chunk)
        args["area"] = _split_args(args["area"])
        res = Response(csvmatch.geocoding_request_csv(args, buf))
        res.content_type = f"text/csv; charset={args['oenc']}"
        res.headers["Content-Disposition"] = \
            "attachment; filename={}".format(
                urllib.parse.quote(args['filename']))
        return res
    except ValueError as e:
        flash("パラメータが正しくありません： {}".format(e), 'danger')
    except UnicodeEncodeError:
        flash((
            "入力文字エンコーディングの自動認識に失敗したか、"
            "指定されたエンコーディングで変換できませんでした。"
            "オプション項目で正しいエンコーディングを指定してください。"
        ))
    except csv.Error:
        flash(
            f"ファイル '{args['filename']}' をCSVとして解析できませんでした。",
            "danger")
    except RuntimeError as e:
        flash(
            "送信データの解析に失敗しました。エラー: {}".format(e),
            'danger')

    return csvmatch.return_error_response(input_args)


@app.route("/license")
def license():
    dictionary_readme = jageocoder.installed_dictionary_readme()
    return render_template(
        'license.html',
        readme=dictionary_readme)


@app.route("/webapi")
def webapi():
    root_url = request.url.replace(url_for('webapi'), '')
    # url = url_for('geocode', addr='西新宿2丁目8-1', area='東京都', opts='all')
    params = {
        "addr": os.environ.get('GEOCODING_REQUEST_PARAM_ADDR', '西新宿2丁目8-1'),
        "area": os.environ.get('GEOCODING_REQUEST_PARAM_AREA', '東京都'),
        "opts": os.environ.get('GEOCODING_REQUEST_PARAM_OPTS', 'all'),
        "rlat": float(os.environ.get(
            'RGEOCODING_REQUEST_PARAM_LAT', '35.689472')),
        "rlon": float(os.environ.get(
            'RGEOCODING_REQUEST_PARAM_LON', '139.69175')),
        "rlevel": int(os.environ.get('RGEOCODING_REQUEST_PARAM_LEVEL', '7')),
        "ropts": os.environ.get('RGEOCODING_REQUEST_PARAM_OPTS', 'all'),
    }
    url = url_for(
        'geocode',
        addr=params["addr"],
        area=params["area"],
        opts=params["opts"],
    )
    geocoding_api_url = os.environ.get('SITE_ROOT_URL', root_url) + url
    with app.test_request_context(url):
        res = app.dispatch_request()
        geocoding_result = json.dumps(
            json.loads(res.get_data(as_text=True)),
            indent=2,
            ensure_ascii=False,
        )

    if use_rgeocoder:
        url = url_for(
            'reverse_geocode',
            lat=params["rlat"],
            lon=params["rlon"],
            level=params["rlevel"],
            opts=params["ropts"],
        )
        rgeocoding_api_url = os.environ.get('SITE_ROOT_URL', root_url) + url
        with app.test_request_context(url):
            res = app.dispatch_request()
            rgeocoding_result = json.dumps(
                json.loads(res.get_data(as_text=True)),
                indent=2,
                ensure_ascii=False,
            )

    else:
        rgeocoding_result = ""
        rgeocoding_api_url = "（このサーバでは利用できません）"

    return render_template(
        'webapi.html',
        params=params,
        geocoding_result=geocoding_result,
        rgeocoding_result=rgeocoding_result,
        geocoding_api_url=geocoding_api_url,
        rgeocoding_api_url=rgeocoding_api_url,
    )


@app.route("/search", methods=['POST', 'GET'])
def search():
    options = get_query_options(request)
    if options['q']:
        jageocoder.set_search_config(
            aza_skip=options['skip_aza'],
            require_coordinates=(options['req_coords'] == 'on'),
            best_only=(options['best_only'] == 'on'),
            auto_redirect=(options['auto_redirect'] == 'on'),
            target_area=_split_args(options['area']),
        )
        results = jageocoder.searchNode(query=options['q'])
    else:
        results = []

    if len(results) == 1:
        return redirect(url_for('show_node', id=results[0].node.id))

    if len(results) > 1:
        nodes = [x.node for x in results]
        return render_template(
            'node_list.html',
            tree=tree,
            nodes=nodes)

    response = make_response(render_template(
        'index.html',
        **options,
        results=results,
    ))
    return set_query_options(response, options)


@app.route("/node/<id>", methods=['POST', 'GET'])
def show_node(id):
    node = tree.get_node_by_id(int(id))
    options = get_query_options(request)

    response = make_response(render_template(
        'node.html',
        tree=tree,
        node=node,
        node_by_level=node.get_nodes_by_level(),
        **options,
    ))
    return set_query_options(response, options)


def _node2dict(node: AddressNode, options: List[str]) -> dict:
    result = node.as_dict()
    if "postcode" in options or "all" in options:
        result["postcode"] = node.get_postcode()

    if "azaid" in options or "all" in options:
        result["azaid"] = node.get_aza_id()

    if "prefcode" in options or "all" in options:
        result["prefcode"] = node.get_pref_jiscode()

    if "citycode" in options or "all" in options:
        result["citycode"] = node.get_city_jiscode()

    if "lgcode" in options or "all" in options:
        result["lgcode"] = node.get_city_local_authority_code()

    return result


@app.route("/geocode", methods=['POST', 'GET'])
@cross_origin()
def geocode():
    if request.method == 'GET':
        query = request.args.get('addr', '')
        area = request.args.get('area', '')
        skip_aza = request.args.get('skip_aza', 'auto')
        options = request.args.get('opts', '')
    else:
        query = request.form.get('addr', '')
        area = request.form.get('area', '')
        skip_aza = request.form.get('skip_aza', 'auto')
        options = request.form.get('opts', '')

    if query:
        jageocoder.set_search_config(
            best_only=True,
            auto_redirect=True,
            target_area=_split_args(area),
            aza_skip=skip_aza)
        results = jageocoder.searchNode(query=query)
    else:
        return "'addr' is required.", 400

    options = options.split(",")
    results = [
        {"node": _node2dict(r.node, options), "matched": r.matched}
        for r in results
    ]
    return jsonify(results), 200


@app.route("/rgeocode", methods=['POST', 'GET'])
@cross_origin()
def reverse_geocode():
    if not use_rgeocoder:
        return "'rgeocode' is not available on this server.", 400

    if request.method == 'GET':
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        level = request.args.get('level', AddressLevel.AZA)
        options = request.args.get('opts', '')
    else:
        lat = request.form.get('lat')
        lon = request.form.get('lon')
        level = request.form.get('level', AddressLevel.AZA)
        options = request.form.get('opts', '')

    if lat and lon:
        results = jageocoder.reverse(
            x=float(lon),
            y=float(lat),
            level=int(level),
            as_dict=False
        )
    else:
        return "'lat' and 'lon' are required.", 400

    options = options.split(",")
    results = [
        {"candidate": _node2dict(r["candidate"], options), "dist": r["dist"]}
        for r in results
    ]
    return jsonify(results), 200


def get_query_options(request) -> None:
    defaults = {
        'q': '',
        'area': '',
        'auto_redirect': 'on',
        'skip_aza': 'auto',
        'req_coords': 'on',
        'best_only': 'on',
    }
    options = {}
    for opt in defaults.keys():
        options[opt] = request.args.get(
            opt,
            request.cookies.get(opt, defaults[opt])
        )

    return options


def set_query_options(
    response: Response,
    options: dict
) -> Response:
    for key, value in options.items():
        response.set_cookie(key, value)

    return response


#
# JSON-RPC methods
#

@jsonrpc.method("jageocoder.server_signature")
def remote_server_signature() -> str:
    """
    Return the running server signature.

    Note
    ----
    - This is used to check that the server has not been restarted,
        since the node ID changes when the dictionary is updated.
    """
    return server_signature


@jsonrpc.method("jageocoder.installed_dictionary_version")
def module_installed_dictionary_version() -> str:
    """
    Return the installed dictionary version.
    """
    return dictionary_version


@jsonrpc.method("jageocoder.installed_dictionary_readme")
def module_installed_dictionary_readme() -> str:
    """
    Return the installed dictionary README.
    """
    return jageocoder.installed_dictionary_readme()


@jsonrpc.method("jageocoder.search")
def module_search(
    query: str,
    config: dict,
) -> dict:
    """
    Return the 'search' result.

    Note
    ----
    - Since JSON-RPC is stateless, the 'search_config' parameters
        are required every time.
    """
    if not query:
        raise ValueError("'query' is required.")

    jageocoder.set_search_config(**config)
    result = jageocoder.search(query=query)
    return result


@jsonrpc.method("jageocoder.searchNode")
def module_searchNode(
    query: str,
    config: dict,
) -> list:
    """
    Return the 'searchNode' result.

    Note
    ----
    - Since JSON-RPC is stateless, the 'search_config' parameters
        are required every time.
    """
    if not query:
        raise ValueError("'query' is required.")

    jageocoder.set_search_config(**config)
    search_results = jageocoder.searchNode(query=query)
    results = []
    for r in search_results:
        results.append(r.as_dict())

    return results


@jsonrpc.method("node.get_record")
def node_get_record(
    pos: int,
    server: str,
) -> dict:
    """
    Return the node information specified by its pos (id).

    Note
    ----
    - Since the 'node ID' changes when the dictionary is updated,
        this method requires the server signature for confirmation.
    """

    if server != server_signature:
        raise RuntimeError((
            "Server signature does not match."
            "The server may have been restarted."
        ))

    record = tree.address_nodes.get_record(pos)
    result = record.to_json()
    return result


@jsonrpc.method("node.count_records")
def node_count_records() -> int:
    """
    Return the number of records in the database.
    """
    n = tree.address_nodes.count_records()
    return n


@jsonrpc.method("node.search_records_on")
def node_search_records_on(
    attr: str,
    value: str,
    funcname: str,
    server: str,
) -> list:
    """
    Search records by its attr and value.

    Notes
    -----
    - This method returns the list of jsoned address nodes.
    """
    if server != server_signature:
        raise RuntimeError((
            "Server signature does not match."
            "The server may have been restarted."
        ))

    records = tree.address_nodes.search_records_on(
        attr=attr, value=value, funcname=funcname)
    results = []
    for record in records:
        results.append(record.to_json())

    return results


@jsonrpc.method("dataset.get")
def dataset_get(id: int) -> dict:
    """
    Return the dataset information specified by its id.
    """
    datasets = tree.address_nodes.datasets
    return datasets.get(id)


@jsonrpc.method("dataset.get_all")
def dataset_get_all() -> dict:
    """
    Return the all dataset information
    """
    datasets = tree.address_nodes.datasets
    return datasets.get_all()


@jsonrpc.method("jageocoder.reverse")
def module_reverse(
    x: float,
    y: float,
    level: int,
) -> list:
    """
    Return the 'reverse' result.
    """
    if use_rgeocoder is False:
        raise RuntimeError(
            "This server does not provide reverse geocoding service."
        )

    reverse_results = jageocoder.reverse(
        x=x, y=y, level=level, as_dict=True
    )
    return reverse_results


@jsonrpc.method("aza_master.search_by_codes")
def azamaster_search_by_codes(
    code: str,
) -> dict:
    """
    Search Address-base-registry's aza records.
    """
    record = tree.aza_masters.search_by_code(code)
    if isinstance(record, dict):
        return record

    result = {
        "code": record.code,
        "names": record.names,
        "namesIndex": record.namesIndex,
        "azaClass": record.azaClass,
        "isJukyo": record.isJukyo,
        "startCountType": record.startCountType,
        "postcode": record.postcode,
    }
    return result
