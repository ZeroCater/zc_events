from six import binary_type, text_type
from unittest import TestCase
from zc_events.utils import model_to_dict


class ExampleModel(object):
    def __init__(self):
        self.control_attr = 'test'


class ModelToDictTests(TestCase):

    def dictify(self):
        attr_dict = {x: x for x in ['test_attr', 'control_attr']}
        return model_to_dict(self.test_model, attr_dict)

    def setUp(self):
        self.test_model = ExampleModel()

    def test_control_attr(self):
        self.test_model.test_attr = 'fdsa'
        model_dict = self.dictify()
        self.assertIn('control_attr', list(model_dict.keys()))
        self.assertIn('test', list(model_dict.values()))

    def test_instance__and_returned_attr_names(self):
        self.test_model.instance_attr = 'foobar'
        attr_dict = {'returned_attr': 'instance_attr', 'control_attr': 'control_attr'}
        model_dict = model_to_dict(self.test_model, attr_dict)
        expected_dict = {'returned_attr': 'foobar', 'control_attr': 'test'}
        self.assertEqual(model_dict, expected_dict)

    def test_none_attr(self):
        self.test_model.test_attr = None
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': None, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), type(None))

    def test_int_attr(self):
        self.test_model.test_attr = 123
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': 123, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), int)

    def test_float_attr(self):
        self.test_model.test_attr = 123.456
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': 123.456, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), float)

    def test_bool_attr(self):
        self.test_model.test_attr = False
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': False, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), bool)

        self.test_model.test_attr = True
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': True, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), bool)

    def test_bytes_attr(self):
        self.test_model.test_attr = 'asdf'.encode('utf-8')
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': 'asdf'.encode('utf-8'), 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), binary_type)

    def test_str_attr(self):
        self.test_model.test_attr = text_type('asdf')
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': text_type('asdf'), 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), text_type)

    def test_list_attr(self):
        self.test_model.test_attr = [1, 'foo']
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': [1, 'foo'], 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), list)

    def test_dict_attr(self):
        self.test_model.test_attr = {'foo': 123}
        model_dict = self.dictify()
        self.assertEqual(model_dict, {'test_attr': {'foo': 123}, 'control_attr': 'test'})
        self.assertEqual(type(model_dict['test_attr']), dict)
