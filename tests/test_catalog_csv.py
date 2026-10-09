import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog_csv', ROOT/'addons/auto_parts_dealer/models/catalog_csv.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT/'examples/catalog.csv').read_bytes()

    def test_valid_and_deterministic(self):
        rows, digest = module.parse_catalog(self.raw)
        self.assertEqual(len(rows), 2)
        self.assertEqual(digest, module.parse_catalog(self.raw)[1])

    def test_duplicate_identifiers(self):
        for original, duplicate in [(b'DEMO-PAD-001', b'DEMO-FILTER-001'), (b'DEMO-BP-001', b'DEMO-OF-001'), (b'DEMO000002', b'DEMO000001')]:
            with self.subTest(original=original), self.assertRaises(ValueError):
                module.parse_catalog(self.raw.replace(original, duplicate))

    def test_nonfinite_negative_or_overprecise_money(self):
        for value in [b'NaN', b'Infinity', b'-1', b'0.00001', b'1000000001']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.parse_catalog(self.raw.replace(b'24.50', value))

    def test_bad_shape_encoding_size_and_relations(self):
        for raw in [b'bad', b'\xff', b'x'*2100000, self.raw.replace(b'uom.product_uom_unit', b'Unit'), self.raw.replace(b',new,', b',unknown,'), self.raw.replace(b'source_key,name', b'name,source_key')]:
            with self.assertRaises(ValueError):module.parse_catalog(raw)


if __name__ == '__main__':unittest.main()
