#! /Library/Frameworks/Python.framework/Versions/2.7/bin/python
#  $Id$
import sys, copy,  os, ConfigParser, pprint
from docutils_fo_dicts import *
from xml.sax import saxutils
class FOConfigFileException(Exception):
    pass

def dump(object):
    pp = pprint.PrettyPrinter(indent=4)
    sys.stderr.write(pp.pformat(object))
    sys.stderr.write('\n')


class Dump:
    def __init__(self):
        pass

class WriteStylesheet:

    def __init__(self, verbose = 0):
        self.__verbose = verbose
        self.__string = ''

    def __write_start_element(self, name, atts):
        pass

    def __write_end_element(self, name):
        pass

    def __write_root_start(self):
        self.__string +=  """<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    version="1.1"
    >\n\n"""
        pass

    def __write_root_end(self):
        self.__string +='</xsl:stylesheet>'

    def __write_att_sets(self):
        self.__string += '\n     <!--ATTRIBUTE SETS-->\n\n'
        att_sets = self.__att_sets.keys()
        for att_set in att_sets:
            self.__string += '     <xsl:attribute-set name="%s">\n' % (att_set)
            att_dict = self.__att_sets[att_set]
            atts = att_dict.keys()
            for att in atts:
                self.__string += '          <xsl:attribute name="%s">' % (att)
                self.__string += saxutils.escape(att_dict[att])
                self.__string += '</xsl:attribute>\n' 

            self.__string += '     </xsl:attribute-set>\n\n'

    def __write_import(self):
        self.__string += """     <xsl:import href= "%s"/>\n\n""" % (self.__import_ss)

    def __write_params(self):
        self.__string += '\n     <!--PARAMS-->\n\n'
        the_keys = self.__params.keys()
        the_keys.sort()
        for the_key in the_keys:
            value =  saxutils.escape(self.__params[the_key])
            self.__string += '     <xsl:param name = "%s">%s</xsl:param>\n' % (the_key, value)
        self.__string += '\n\n'

    def write_stylesheet(self, import_ss, params, att_sets, out=None):
        self.__import_ss = import_ss
        self.__params = params
        self.__att_sets = att_sets
        self.__out = out
        self.__write_root_start()
        self.__write_import()
        self.__write_params()
        self.__write_att_sets()
        self.__write_root_end()
        return self.__string

class PostProcess:

    def __init__(self, params, attribute_sets):
        self.__attribute_sets = attribute_sets
        self.__params = params


    # not used
    def __test_measure(self, the_string):
        """
        test if string is a measure:
        12pt returns 12, pt
        1.5 returns None, None

        """
        accept_units = ['em', 'px', 'in', 'cm', 'mm', 'pt', 'pc']
        try:
            float(the_string)
            return None, None
        except ValueError:
            pass
        if len(the_string) < 3:
            return None, None
        unit = the_string[-2:]
        if unit not in accept_units:
            return None, None
        num = the_string[:-2]
        try:
            num = float(num)
        except ValueError:
            return None, None
        return num, unit

    # not used
    def __get_default_font_size(self):
        document_att_set = self.__attribute_sets.get('default-page-sequence')
        body_att_set = self.__attribute_sets.get('default-flow')
        if document_att_set and document_att_set.get('font-size'):
            default_font_size = document_att_set.get('font-size')
        elif body_att_set and document_att_set.get('font-size'):
            default_font_size = body_att_set.get('font-size')
        else:
            default_font_size = '12pt'
        num, unit = self.__test_measure(default_font_size)
        if not num:
            default_font_size = '12pt'
        self.__default_font_size = default_font_size

    def __fix_header_footer(self):
        # have to set the param spacing-header to extent, if not already set
        header_att_set = self.__attribute_sets.get('header-region-before')
        if header_att_set:
            extent = header_att_set.get('extent')
            if extent and not self.__params.get('spacing-header'):
                self.__params['spacing-header'] = extent

        footer_att_set = self.__attribute_sets.get('footer-region-after')
        if footer_att_set:
            extent = footer_att_set.get('extent')
            if extent and not self.__params.get('spacing-footer'):
                self.__params['spacing-footer'] = extent

        # have to add a space-before.conditionality to force space that
        # otherwise would not be written
        header_att_set = self.__attribute_sets.get('header-block')
        if header_att_set:
            space_before = header_att_set.get('space-before')
            if space_before:
                self.__attribute_sets['header-block']['space-before.conditionality'] = 'retain'

        # same as above
        footer_att_set = self.__attribute_sets.get('footer-block')
        if footer_att_set:
            space_before = footer_att_set.get('space-before')
            if space_before:
                self.__attribute_sets['footer-block']['space-before.conditionality'] = 'retain'

    def __get_page_layout(self):
        odd_page = self.__attribute_sets.get('odd-simple-page-master')
        even_page = self.__attribute_sets.get('even-simple-page-master')
        first_page = self.__attribute_sets.get('first-simple-page-master')
        suppress_first_header = self.__params.get('suppress-first-page-header')
        suppress_first_footer = self.__params.get('suppress-first-page-footer')
        need_odd_or_even_page = False
        if odd_page or even_page:
            need_odd_or_even_page = True
        need_first_page = False
        if suppress_first_footer or suppress_first_header or first_page:
            need_first_page = True

        if need_first_page and need_odd_or_even_page:
            page_layout = 'first-odd-even'
        elif need_first_page:
            page_layout = 'first'
        elif need_odd_or_even_page:
            page_layout = 'odd-even'
        else:
            page_layout = 'simple'
        self.__params['page-layout'] = page_layout
        



    def post_process(self):
        self.__get_default_font_size()
        self.__fix_header_footer()
        self.__get_page_layout()
        return self.__attribute_sets, self.__params

class ReadConfig:

    def __init__(self, import_ss = None, verbose = 0):
        self.__verbose = verbose
        if self.__verbose > 4:
            sys.stderr.write('modules is "%s"\n' % __file__)
        self.__attribute_sets = {}
        self.__params = {}
        self.__import_ss = import_ss
        if not self.__import_ss:
            self.__import_ss = os.path.join(os.path.dirname(__file__), 'xsl_fo','docutils_to_fo.xsl') 
        if os.sep != '/':
            self.__correct_path = self.__correct_path(self.__import_ss)
        if not os.path.isfile(self.__import_ss):
            msg = '"%s" cannot be found\n' % (self.__import_ss)
            raise FOConfigFileException(msg)
        if self.__verbose > 3:
            sys.stderr.write('self.__import_ss (stylesheet to import) is "%s" \n' % self.__import_ss)

    def __correct_path(self, the_path):
        """
        make sure the_path is os.path.abs(the_path) and that
        the_path really exits or this may not work

        """
        paths = []
        head = None
        counter = 1
        while 1:
            counter += 1
            if not head:
                head = the_path
            head, tail = os.path.split(head)
            paths.insert(0,tail)
            if not tail: 
                break
            if counter > 100:
                raise RuntimeError, 'max num recursions (100) reached'
        return '/'.join(paths)

    def write_config_file(self, dest=None):
        w = WriteStylesheet()
        ss_string = w.write_stylesheet(import_ss = self.__import_ss, params = self.__params, 
                att_sets = self.__attribute_sets)
        return ss_string


    def read_config_files(self):
        config = ConfigParser.SafeConfigParser()
        config_files = []
        if os.environ.get('HOME'):
            config_files.append(os.path.join(os.environ.get('HOME'), '.docutils'))
        config_files.append(os.path.join(os.getcwd(), 'docutils.conf'))
        for the_path in config_files:
            config.read(the_path)
        if self.__verbose > 4:
            sys.stderr.write('config is: \n' )
            dump(config.items('FO'))
        return config


    def parse_config_files(self):
        config = self.read_config_files()
        if not 'FO' in config.sections():
            return
        opts =  config.items('FO')
        opts_dict = {}
        for pair_tupple in opts:
            first = pair_tupple[0]
            second = pair_tupple[1]
            fields = first.split('.', 1)
            if prop_as_param_dict.get(first):
                self.__handle_param(prop_as_param_dict.get(first), second)
            elif len(fields) == 2:
                self.__handle_attributes(fields[0], fields[1], second)
            elif first in param_list:
                self.__handle_param(first, second)
            elif first in commands_list:
                pass
            else:
                self.__error('"%s" = "%s" not a valid config option\n' % (first, second))

    def __post_process(self):
        post_process_obj = PostProcess(attribute_sets = self.__attribute_sets, params = self.__params)
        self.__attribute_sets, self.__params = post_process_obj.post_process()
        if self.__verbose > 4:
            sys.stderr.write('self.__attribute_sets after post process:\n')
            dump(self.__attribute_sets)
            sys.stderr.write('self.__params after post process:\n')
            dump(self.__params)
            sys.stderr.write('\n')

    def __handle_attributes(self, user_att_set, user_att, value, check_special = True):
        if  special_atts_dict.get(user_att) and check_special:
            self.__handle_special_atts(user_att_set, user_att, value)
            return
        if  special_att_sets_dict.get(user_att_set) and check_special:
            self.__handle_special_atts(user_att_set, user_att, value)
            return
        set_element = att_set_dict.get(user_att_set)
        if set_element: # found a valid att-set
            att_set = set_element[0] 
            fo_element = set_element[1]
            att = which_dict.get(fo_element).get(user_att)
            if not att:
                self.__error('%s not a valid value for att-set %s' % (user_att, user_att_set))
            else:
                self.__add_attribute(att_set, att, value )
        else:
            self.__error('%s not a valid attribute-set' % (user_att_set))

    def __check_value(self, att, value):
        special = special_values_dict.get(value)
        if special:
            if special[0] == att:
                return special[1]
            else:
                return value
        else:
            return value

    def __add_attribute(self, att_set, att, value):
        att_exists =  self.__attribute_sets.get(att_set)
        if not att_exists:
            self.__attribute_sets[att_set] = {}
        value = self.__check_value(att, value)
        self.__attribute_sets[att_set][att] = value

    def __error(self, msg):
        # sys.stderr.write(msg)
        # sys.stderr.write('\n')
        raise FOConfigFileException(msg)

    def __handle_special_atts(self, user_att_set, user_att, value):
        keep_with = ['keep-with-next', 'keep-with-previous', 'keep-together', 'keep-on-same-page']
        if user_att == 'font-style':
            set_element = att_set_dict.get(user_att_set)
            if not set_element: 
                self.__error('%s not a valid attribute-set' % (user_att_set))
                return
            att_set = set_element[0] 
            att_list = font_style_dict.get(value)
            if not att_list:
                self.__error('%s not a valid value for att-set %s' % (value, user_att))
                return
            else:
                for the_tupple in att_list:
                    self.__add_attribute(att_set, the_tupple[0], the_tupple[1])
        elif user_att_set == 'footer' or user_att_set == 'header':
            if user_att == 'height':
                if user_att_set == 'header':
                    self. __handle_attributes('header-region-before' , 'extent', value)
                if user_att_set == 'footer':
                    self. __handle_attributes('footer-region-after' , 'extent', value)
            elif user_att == 'suppress-first-page' :
                if user_att_set == 'header':
                    self.__handle_param(param = 'suppress-first-page-header', value = value)
                elif user_att_set == 'footer':
                    self.__handle_param(param = 'suppress-first-page-footer', value = value)
            else: 
                if user_att_set == 'header':
                    self. __handle_attributes(user_att_set , user_att, value, check_special = False)
                if user_att_set == 'footer':
                    self. __handle_attributes(user_att_set , user_att, value, check_special = False)
        elif user_att == 'page-break-after' or user_att == 'page-break-before':
            att = user_att[5:]
            true_or_false = true_or_false_dict.get(value)
            if true_or_false == 'True':
                self. __handle_attributes(user_att_set , att, 'page', check_special = False)
                # self.__add_attribute(att_set, 'break-before', 'page')
            elif true_or_false == 'False':
                self. __handle_attributes(user_att_set , att, 'auto', check_special = False)
            else:
                self.__error('%s.%s = %s not a valid attribute property\n' % (user_att_set, user_att, value))

        elif user_att in keep_with:
            true_value = true_dict.get(value)
            if true_value:
                self. __handle_attributes(user_att_set , user_att, 'always', check_special = False)
            else:
                self. __handle_attributes(user_att_set , user_att, value, check_special = False)

        else:
            self.__error('%s.%s = %s not a valid attribute property\n' % (user_att_set, user_att, value))


    def __handle_param(self, param, value):
        to_test_dict = param_dict_test.get(param)
        if to_test_dict:
            correct_value = to_test_dict.get(value)
            if correct_value:
                self.__params[param] = correct_value
            else:
                self.__error('%s = %s not a valid command\n' % (param, value))
        else:
            self.__params[param] = value

    def make_stylesheet(self):
        self.parse_config_files()
        self.__post_process()
        ss_string = self.write_config_file()
        return ss_string
        # self.print_att_list()


if __name__ == '__main__':
    read_config_obj =  ReadConfig(import_ss = '/Users/cynthia/tmp/paultremblay/xsl_fo/docutils_to_fo.xsl' )
    ss_string = read_config_obj.main()
    print ss_string
