import csv
import datetime
import io
from logging import getLogger
import re

import charset_normalizer
from flask import render_template, request, stream_with_context

import jageocoder
from jageocoder.address import AddressLevel


logger = getLogger(__name__)
MAX_READLINE_BYTES = 4096

output_columns = (
    ("ofmtd", ["正規化住所", True]),
    ("ox", ["経度", True]),
    ("oy", ["緯度", True]),
    ("olevel", ["レベル", True]),
    ("omatch", ["一致文字列", False]),
    ("oremain", ["残り文字列", False]),
    ("opref", ["都道府県", False]),
    ("ocounty", ["郡", False]),
    ("ocity", ["市町村・特別区", False]),
    ("oward", ["政令市の区", False]),
    ("oaza", ["町丁目", False]),
    ("oblk", ["街区・地番", False]),
    ("obld", ["住居番号・枝番", False]),
    ("prefcode", ["都道府県コード", False]),
    ("citycode", ["市区町村コード", False]),
    ("municode", ["地方公共団体コード", False]),
    ("abrid", ["ABR町字ID", False]),
    ("oalt", ["他の候補", False]),
)

re_csvline = re.compile(
    r'((\,|\r?\n|\r|^)(?:"([^"]*(?:""[^"]*)*)"|([^"\,\r\n]*)))+',
    re.MULTILINE | re.DOTALL)


def _validate_line_as_csv(line: str) -> bool:
    """
    Validate a line string is complete csv or not.
    """
    if re_csvline.fullmatch(line):
        return True

    return False


def _get_nodes_list_by_level(node: jageocoder.node.AddressNode):
    """
    The function returns an array of this node and its upper nodes.
    The Nth node of the array contains the list of nodes corresponding
    to address level N.
    If there is no element corresponding to level N, [] is stored.

    Example
    -------
    >>> import jageocoder
    >>> jageocoder.init()
    >>> node = jageocoder.searchNode('多摩市落合1-15')[0].node
    >>> [str(x) for x in node.get_nodes_list_by_level()]
    ['[]', '[[12130813:東京都(139.6917724609375,35.68962860107422)1(lasdec:130001/jisx0401:13)]]', '[]', '[[12130813:東京都(139.6917724609375,35.68962860107422)1(lasdec:130001/jisx0401:13)]>[12736747:多摩市(139.4463653564453,35.636959075927734)3(jisx0402:13224/postcode:2060000)]]', '[]', '[[12130813:東京都(139.6917724609375,35.68962860107422)1(lasdec:130001/jisx0401:13)]>[12736747:多摩市(139.4463653564453,35.636959075927734)3(jisx0402:13224/postcode:2060000)]>[12738628:落合(139.42709350585938,35.6248779296875)5()]]', '[[12130813:東京都(139.6917724609375,35.68962860107422)1(lasdec:130001/jisx0401:13)]>[12736747:多摩市(139.4463653564453,35.636959075927734)3(jisx0402:13224/postcode:2060000)]>[12738628:落合(139.42709350585938,35.6248779296875)5()]>[12738629:一丁目(139.42709350585938,35.6248779296875)6(aza_id:0010001/postcode:2060033)]]', '[[12130813:東京都(139.6917724609375,35.68962860107422)1(lasdec:130001/jisx0401:13)]>[12736747:多摩市(139.4463653564453,35.636959075927734)3(jisx0402:13224/postcode:2060000)]>[12738628:落合(139.42709350585938,35.6248779296875)5()]>[12738629:一丁目(139.42709350585938,35.6248779296875)6(aza_id:0010001/postcode:2060033)]>[12738636:15番地(139.42897033691406,35.62577819824219)7()]]']
    """  # noqa: E501
    nodes = []
    cur_node = node
    while cur_node is not None:
        nodes.insert(0, cur_node)
        cur_node = cur_node.parent

    result = [[] for _ in range(20)]
    prev_level = 0
    for n in nodes:
        if n.level < prev_level:
            level = prev_level
        else:
            level = n.level

        result[level].append(n)

    return result


def _geocode_row(row, args, boundary):
    """
    Geocoding 1 line.

    Parameters
    ----------
    row: list[str]
        A row of csv file.
    args: list[str]
        List of web ui paremeters.
    boundary: str
        The boundary string of the current request.
    """
    if len(row) == 0 or boundary in row[0]:
        return None

    newrow = row[:]
    if args['lineno'] == 0 and args['head'] == '1':
        # Process as a header line.
        for oc in output_columns:
            if oc[0] in args:
                newrow.append(oc[1][0])

    else:
        address = ''.join([row[x] for x in args['cols']])
        results = jageocoder.searchNode(query=address)
        if len(results) > 0:
            node = results[0].node
            levels = _get_nodes_list_by_level(node)
            for oc in output_columns:
                if oc[0] not in args:
                    continue

                if oc[0] == 'ofmtd':
                    newrow.append(''.join(node.get_fullname()))
                elif oc[0] == 'ox':
                    newrow.append(node.x if float(node.y) < 90.0 else '')
                elif oc[0] == 'oy':
                    newrow.append(node.y if float(node.y) < 90.0 else '')
                elif oc[0] == 'olevel':
                    newrow.append(node.level)
                elif oc[0] == 'omatch':
                    newrow.append(results[0].matched)
                elif oc[0] == 'oremain':
                    newrow.append(address[len(results[0].matched):])
                elif oc[0] == 'opref':
                    newrow.append(
                        ' '.join([x.name for x in levels[AddressLevel.PREF]]))
                elif oc[0] == 'ocounty':
                    newrow.append(
                        ' '.join(
                            [x.name for x in levels[AddressLevel.COUNTY]])
                    )
                elif oc[0] == 'ocity':
                    newrow.append(
                        ' '.join(
                            [x.name for x in levels[AddressLevel.CITY]])
                    )
                elif oc[0] == 'oward':
                    newrow.append(
                        ' '.join(
                            [x.name for x in levels[AddressLevel.WARD]])
                    )
                elif oc[0] == 'oaza':
                    azanodes = levels[AddressLevel.OAZA] + \
                        levels[AddressLevel.AZA]
                    newrow.append(
                        ' '.join([x.name for x in azanodes])
                    )
                elif oc[0] == 'oblk':
                    newrow.append(
                        ' '.join(
                            [x.name for x in levels[AddressLevel.BLOCK]])
                    )
                elif oc[0] == 'obld':
                    newrow.append(
                        ' '.join(
                            [x.name for x in levels[AddressLevel.BLD]])
                    )
                elif oc[0] == 'prefcode':
                    newrow.append(node.get_pref_jiscode())
                elif oc[0] == 'citycode':
                    newrow.append(node.get_city_jiscode())
                elif oc[0] == 'municode':
                    newrow.append(node.get_city_local_authority_code())
                elif oc[0] == 'abrid':
                    newrow.append(node.get_aza_id())
                elif oc[0] == 'oalt':
                    if len(results) == 1:
                        newrow.append('')
                    else:
                        best = ''.join(node.get_fullname())
                        for r in results[1:]:
                            fullname = ''.join(r.node.get_fullname())
                            if fullname != best:
                                newrow.append(fullname)
                                break
                        else:
                            newrow.append('')

                else:
                    raise ValueError(f"不明なパラメータ '{oc[0]}'")

        else:
            for oc in output_columns:
                if oc[0] in args:
                    newrow.append('')

    args['lineno'] += 1
    return newrow


@stream_with_context
def parse_multipart_formdata():
    """
    Analyze multipart/form-data, and get form parameters.
    """
    m = re.match(
        r'multipart/form-data; boundary=(.*$)',
        request.headers.get('Content-Type'),
        re.IGNORECASE)
    if m is None:
        raise RuntimeError()

    boundary = m.group(1).encode('utf-8')
    mode = 0  # Looking for a boundary
    name = None
    args = {"boundary": boundary}
    while True:
        chunk = request.stream.readline(MAX_READLINE_BYTES)
        if len(chunk) == 0:
            break

        chunk = chunk.rstrip()
        if boundary in chunk:
            mode = 1  # Reading headers
            continue

        if mode == 1:
            if len(chunk) == 0:
                mode = 2  # Reading content
                continue

            line = str(charset_normalizer.from_bytes(chunk).best())
            if line.lower().startswith('content-disposition:'):
                m = re.search(r'name="(.*?)"', line)
                name = m.group(1)
                if name == 'file':
                    m = re.search(r'filename="(.*?)"', line)
                    args['filename'] = m.group(1)

                continue

        if mode == 2:
            if name != 'file':
                line = str(charset_normalizer.from_bytes(chunk).best())
                if name in args:
                    args[name] += line + "\n"
                else:
                    args[name] = line
                continue

            break

    return args, chunk


@stream_with_context
def check_params(args, chunk):
    """
    Check posted form parameters.
    """
    # Check if file is set
    if args['filename'] == '' or len(chunk) == 0:
        raise ValueError("ファイルを指定してください。")

    if args['ofname'] == 'add_dt':
        if args['filename'].lower().endswith('.csv'):
            args['filename'] = args['filename'][:-4]

        args['filename'] += datetime.datetime.now().strftime(
            '_%Y%m%d_%H%M%S.csv')
    elif args['ofname'] == 'dt':
        args['filename'] = datetime.datetime.now().strftime(
            '%Y%m%d_%H%M%S.csv')

    # Confirm if one or more output columns are selected
    for oc in output_columns:
        if oc[0] in args:
            break

    else:
        raise ValueError("出力項目を1つ以上選択してください。")

    # Detect input file encoding
    buffer = chunk + b'\n'
    if args['ienc'] == 'auto':
        for i in range(0, 10):
            result = charset_normalizer.detect(chunk)
            if result['encoding'] is not None:
                args['ienc'] = result['encoding']
                break

            chunk = request.stream.readline(MAX_READLINE_BYTES)
            buffer += chunk
        else:
            args['ienc'] = ""

        if args['ienc'].lower() not in (
                'ascii', 'cp932', 'euc_jp', 'latin_1', 'shift_jis'):
            raise ValueError("文字エンコーディングが判定できません。")

    # Set output file encoding
    if args['oenc'] == 'auto':
        args['oenc'] = args['ienc']

    # Get header line
    if args['head'] == '1':
        while len(buffer) == 0 or _validate_line_as_csv(
                buffer.decode(args['ienc'])) is False:
            buffer += request.stream.readline(MAX_READLINE_BYTES)
            if len(buffer) > MAX_READLINE_BYTES:
                raise csv.Error("This file is not a CSV.")

        # Get header columns
        reader = csv.reader(
            io.StringIO(buffer.decode(args['ienc']))
        )
        args['headers'] = reader.__next__()

    # Select column numbers containing addresses
    cols = []
    if args['cols'].strip() == '':
        raise ValueError('住所を含むカラム番号または列名を入力してください。')

    for col in args['cols'].split(','):
        col = col.strip()
        try:
            col = int(col) - 1
            cols.append(col)
        except ValueError:
            if 'headers' not in args:
                raise ValueError(f'"{col}" は有効な列番号ではありません。')

            if col in args['headers']:
                cols.append(args['headers'].index(col))
            else:
                raise ValueError(f'"{col}" は見出し行にありません。')

    if len(cols) == 0:
        raise ValueError('住所を含むカラム番号または列名を入力してください。')

    args['cols'] = cols

    # Validate target area
    try:
        jageocoder.set_search_config(
            best_only=True,
            aza_skip=None,
            require_coordinates=args['nc'] != '1',
            target_area=args["area"],
        )
    except RuntimeError:
        raise ValueError('対象地域が住所データベースにありません。')

    return args, buffer


@stream_with_context
def geocoding_request_csv(args, buffer):
    # Geocoding csv file
    boundary = args['boundary'].decode(args['ienc'])
    output = io.StringIO()
    writer = csv.writer(output)
    args['lineno'] = 0

    if len(buffer) > 0:
        reader = csv.reader(io.StringIO(buffer.decode(args['ienc'])))
        for row in reader:
            r = _geocode_row(row, args, boundary=boundary)
            if r is None:
                break

            output.truncate(0)
            output.seek(0)
            writer.writerow(r)
            line = output.getvalue()
            if args['oenc'].lower() != 'utf-8':
                line = line.encode(args['oenc'])

            yield line

    textio = io.TextIOWrapper(request.stream, encoding=args['ienc'])
    reader = csv.reader(textio)
    for row in reader:
        r = _geocode_row(row, args, boundary=boundary)
        if r is None:
            break

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(r)
        line = output.getvalue()
        if args['oenc'].lower() != 'utf-8':
            line = line.encode(args['oenc'])

        yield line

    request.stream.read()
    return


def return_error_response(input_args):
    """
    Return rendered respons for error.

    Note
    ----
    This method must not be with the streaming context.
    """
    d = True
    while d:
        # Consume all incomming stream...
        # There should be other way to close the socket.
        d = request.stream.read(MAX_READLINE_BYTES * 16)
        logger.debug("Read {} bytes.".format(len(d)))

    request.close()
    return render_template(
        'csv.html',
        columns=output_columns,
        args=input_args)
