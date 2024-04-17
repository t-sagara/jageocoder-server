import copy
import csv
import json
from typing import List
import os
from pathlib import Path
import re
import urllib

import dotenv
from flask_cors import cross_origin
from flask import Flask, flash, request, render_template, jsonify, \
    Response, url_for, make_response

import jageocoder
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode

jageocoder.init()
module_version = jageocoder.__version__
dictionary_version = jageocoder.installed_dictionary_version()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.json.ensure_ascii = False

# Load environment variables from ".env", if exists.
envpath = Path(__file__).parent / 'secret/.env'
if envpath.exists:
    dotenv.load_dotenv(envpath)

tree_dir = Path(jageocoder.get_module_tree().db_dir)
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
    tree = jageocoder.get_module_tree()
    aza_node = tree.aza_masters.search_by_code(code)

    if aza_node:
        names = json.loads(aza_node.names)
    else:
        names = None

    return render_template(
        'aza.html',
        tree=tree,
        aza=aza_node, names=names)


@app.route("/aza/<aza_id>", methods=['POST', 'GET'])
def search_aza_id(aza_id):
    tree = jageocoder.get_module_tree()
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
    tree = jageocoder.get_module_tree()
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
    tree = jageocoder.get_module_tree()
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
    tree = jageocoder.get_module_tree()
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
    url = url_for('geocode', addr='西新宿2丁目8-1', area='東京都', opts='all')
    geocoding_api_url = os.environ.get('SITE_ROOT_URL', root_url) + url
    with app.test_request_context(url):
        res = app.dispatch_request()
        geocoding_result = json.dumps(
            json.loads(res.get_data(as_text=True)),
            indent=2,
            ensure_ascii=False,
        )

    if use_rgeocoder:
        url = url_for('reverse_geocode', lat=35.689472,
                      lon=139.69175, level=7, opts='all')
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
        results = None

    response = make_response(render_template(
        'index.html',
        **options,
        results=results,
    ))
    return set_query_options(response, options)


@app.route("/node/<id>", methods=['POST', 'GET'])
def show_node(id):
    tree = jageocoder.get_module_tree()
    node = tree.get_node_by_id(int(id))
    options = get_query_options(request)

    response = make_response(render_template(
        'node.html',
        tree=tree,
        node=node,
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
        {"node": _node2dict(r.node, options), "mached": r.matched}
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
