import math
import unittest

from world_binary_questions import (category_codes, evaluate_binary,
                                    literal_threshold, validate_predicate)


class BinaryQuestionsTest(unittest.TestCase):
    def test_cyrus_red_count_examples_and_equality_boundaries(self):
        for value, comparator, cutoff, expected in (
            (5, '>', '0', 'YES'), (5, '>', '4', 'YES'),
            (5, '>=', '3', 'YES'), (0, '>=', '1', 'NO'),
            (3, '>', '3', 'NO'), (3, '>=', '3', 'YES'),
            (3, '=', '3', 'YES'), (3, '!=', '3', 'NO'),
            (3, '<=', '3', 'YES'), (3, '<', '3', 'NO')):
            with self.subTest(value=value, comparator=comparator, cutoff=cutoff):
                self.assertEqual(evaluate_binary(value, comparator, cutoff,
                                 feature_kind='integer_count').answer, expected)

    def test_missing_and_not_yet_known_are_excluded_never_no(self):
        for value, known in ((None, True), (math.nan, True), (0, False), (5, False)):
            result = evaluate_binary(value, '>', '4', known=known)
            self.assertEqual(result.answer, 'NOT_EVALUABLE')
            self.assertFalse(result.evaluable)
            self.assertIsNone(result.nullable_bool())
            self.assertTrue(result.reason)
            with self.assertRaises(TypeError):
                bool(result)

    def test_known_zero_is_a_no_and_known_infinity_is_not_missing(self):
        self.assertIs(evaluate_binary(0, '>', '0').nullable_bool(), False)
        self.assertIs(evaluate_binary(math.inf, '>', '1.5').nullable_bool(), True)
        self.assertEqual(evaluate_binary(-math.inf, '<', '0').answer, 'YES')

    def test_strict_shape_threshold_has_no_epsilon(self):
        self.assertEqual(evaluate_binary(.9, '>', '.9').answer, 'NO')
        self.assertEqual(evaluate_binary(math.nextafter(.9, math.inf), '>', '.9').answer, 'YES')
        self.assertEqual(evaluate_binary(math.nextafter(.9, -math.inf), '>', '.9').answer, 'NO')

    def test_integer_counts_do_not_lose_bits_above_binary64_precision(self):
        value = 2**53 + 1
        self.assertEqual(evaluate_binary(value, '>', str(2**53), feature_kind='integer_count').answer, 'YES')
        self.assertEqual(evaluate_binary(value, '=', str(value)+'.0', feature_kind='integer_count').answer, 'YES')
        self.assertEqual(evaluate_binary(value, '<', str(value)+'.1', feature_kind='integer_count').answer, 'YES')
        self.assertEqual(evaluate_binary(2**53, '<', str(value)).answer, 'YES')

    def test_literal_numbers_are_required_not_expressions_or_missing_tokens(self):
        for bad in ('NaN', 'Infinity', 'inf', '', ' 3', '3 ', '01', '.5.6', '2 * ATR', 'q80', '1e-9999'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                literal_threshold(bad)
        for bad in ('above', '==', '=>', '>= 3'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_predicate(bad, '3')

    def test_categorical_feature_is_split_into_codebook_bound_binary_equalities(self):
        book = category_codes('{"0":"none","1":"bull_div","2":"bear_div"}')
        self.assertEqual(evaluate_binary(1, '=', '1', feature_kind='category_code', categories=book).answer, 'YES')
        self.assertEqual(evaluate_binary(1, '=', '2', feature_kind='category_code', categories=book).answer, 'NO')
        for comparator, threshold in (('>', '1'), ('=', '3'), ('=', '1.5')):
            with self.assertRaises(ValueError):
                validate_predicate(comparator, threshold, 'category_code', book)
        with self.assertRaises(ValueError):
            evaluate_binary(3, '=', '1', feature_kind='category_code', categories=book)

    def test_codebooks_cannot_hide_duplicate_codes_labels_or_missing_codes(self):
        for bad in ('{"0":"a","0":"b"}', '{"0":"a","1":"a"}', '{"-1":"missing"}',
                    '{"01":"a"}', '{}', '["a"]', '{"0":null}'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                category_codes(bad)

    def test_bad_measurement_types_and_flags_do_not_silently_become_numeric_answers(self):
        for value in ('3', True, complex(3, 0)):
            with self.assertRaises(TypeError):
                evaluate_binary(value, '>', '2')
        with self.assertRaises(TypeError):
            evaluate_binary(0, '>', '2', known='false')
        for value in (-1, .5, math.inf):
            with self.assertRaises(ValueError):
                evaluate_binary(value, '>', '0', feature_kind='integer_count')
        self.assertEqual(evaluate_binary(True, '=', '1', feature_kind='boolean').answer, 'YES')
        self.assertEqual(evaluate_binary(False, '=', '1', feature_kind='boolean').answer, 'NO')


if __name__ == '__main__':
    unittest.main()
