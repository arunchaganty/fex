import logging
import re

logger = logging.getLogger(__name__)

class QuerySchema():
    def __init__(self, json):
        self.json = json
        self.fields = { f['name'] : f for f in json.get('fields') }
        self.types = { t['name'] : t for t in json.get('types') }

        def get_fields(f, prefix=[], all_fields=[]):
            # print('processing {}'.format(f))
            if isinstance(f, list):
                for x in f:
                    get_fields(x, prefix, all_fields)
            elif 'type' in f and f['type'] in self.types:
                ftype = self.types[f['type']]
                get_fields(ftype['fields'], prefix + [f['name']])
            else:
                path = prefix + [f['name']]
                all_fields.append({ 'name': '.'.join(path), 'path': path, 'type': f['type']})
            return all_fields

        all_fields = get_fields(json.get('fields'))
        self.all_fields = { f['name'] : f for f in all_fields }
        self.text_fields = { f['name'] : f for f in all_fields if f['type'] == 'text' }

    def has_field(self, name):
        okay = name in self.all_fields
        if not okay:
            parts = name.split('.')
            if len(parts) > 1:
                cname = '.'.join(parts[:-1])
                f = self.all_fields.get(cname)
                if f is not None and f['type'] == 'counts':
                    okay = True
        return okay


def or_filter(fieldnames, fieldvalue, check_value=None):
    # print('filter {} {}'.format(fieldnames, fieldvalue))
    if check_value is None:
        check_value = lambda sv, tv: str(tv) == sv

    def check_field(elem, path, searchvalue):
        if len(path) == 0:
            if searchvalue == '*':
                if elem is not None:
                    return True
            elif check_value(searchvalue, elem):
                return True
        else:
            fieldname = path[0]
            if isinstance(elem, dict):
                elem_value = elem.get(fieldname)
                if elem_value is not None:
                    if isinstance(elem_value, list):
                        # check any of the values
                        for v in elem_value:
                          if check_field(v, path[1:], searchvalue):
                            return True
                    else:
                        return check_field(elem_value, path[1:], searchvalue)
        return False
    def f(elem):
        for fieldname in fieldnames:
            path = fieldname.split('.')
            if check_field(elem, path, fieldvalue):
                return True
    return f

def neg_filter(f):
    return lambda elem: not f(elem)

def smart_split(text, delimiter, trim_quotes=False):
    def replacer(m):
        return m.group(0).replace(delimiter, "\x00")
    parts = re.sub('".+?"', replacer, text).split(delimiter)
    parts = [p.replace("\x00", delimiter) for p in parts]
    if trim_quotes:
        parts = [p[1:-1] if p.startswith('"') and p.endswith('"') else p for p in parts]
    return parts


def find_records(lst, query_str, schema=None):
    conditions = smart_split(query_str, ' ')
    filters = []
    text_fields = schema.text_fields.keys() if schema else []
    # logger.info('text_fields {}'.format(text_fields))
    for condition in conditions:
        isNot = False
        if condition.startswith('!'):
            condition = condition[1:]
            isNot = True
        parts = smart_split(condition, ':', trim_quotes=True)
        logger.info('Searching for {}'.format(parts))
        if len(parts) == 1:
            filt = or_filter(text_fields, parts[0], check_value = lambda sv, tv: sv in tv)
            filt = neg_filter(filt) if isNot else filt
            filters.append(filt)
        elif len(parts) == 2:
            if schema and not schema.has_field(parts[0]):
                logger.warn('Unknown search field {}'.format(parts[0]))
            filt = or_filter([parts[0]], parts[1])
            filt = neg_filter(filt) if isNot else filt
            filters.append(filt)
        else:
            raise Exception('Invalid query string to find_records')
    def filter_record(elem):
        for f in filters:
            if not f(elem):
                return False
        return True
    return [(i,rec) for i,rec in enumerate(lst) if filter_record(rec)]


def find_record_indices(lst, query_str, schema=None):
    return [i for i,rec in find_records(lst, query_str, schema)]
