import unittest
from app.classify import classify_query, detect_topic, detect_scheme

class TestClassifyQuery(unittest.TestCase):
    def test_factual_basic(self):
        self.assertEqual(classify_query("What is the expense ratio of this fund?"), "FACTUAL")
        self.assertEqual(classify_query("Show me the NAV for yesterday."), "FACTUAL")
        self.assertEqual(classify_query("Where can I download statement?"), "FACTUAL")
        self.assertEqual(classify_query("Is there an exit load?"), "FACTUAL")
        self.assertEqual(classify_query("What is the benchmark of the large-cap mutual fund?"), "FACTUAL")

    def test_advisory_basic(self):
        self.assertEqual(classify_query("Should I invest in this?"), "ADVISORY")
        self.assertEqual(classify_query("Which is better for me, ELSS or Flexi cap?"), "ADVISORY")
        self.assertEqual(classify_query("What are the expected returns?"), "ADVISORY")
        self.assertEqual(classify_query("Please recommend a top performing scheme."), "ADVISORY")
        self.assertEqual(classify_query("Is this a good investment right now?"), "ADVISORY")

class TestDetectTopic(unittest.TestCase):
    def test_expense_ratio_variations(self):
        self.assertEqual(detect_topic("What is the EXPENSE RATIO?"), "expense_ratio")
        self.assertEqual(detect_topic("what is the ter"), "expense_ratio")
    
    def test_lock_in_variations(self):
        self.assertEqual(detect_topic("Does it have a LOCK-IN period?"), "lock_in")
        self.assertEqual(detect_topic("What is the Lock IN"), "lock_in")
        
    def test_statement_download_variations(self):
        self.assertEqual(detect_topic("I want to DownLoad my Statement"), "statement_download")
        self.assertEqual(detect_topic("Show me the CAPITAL GAINS"), "statement_download")

class TestDetectScheme(unittest.TestCase):
    def test_large_cap_variations(self):
        self.assertEqual(detect_scheme("I want to invest in BlueChip funds"), "large_cap")
        self.assertEqual(detect_scheme("Large Cap or LargeCap?"), "large_cap")
        
    def test_elss_variations(self):
        self.assertEqual(detect_scheme("Is this an ELSS fund?"), "elss")
        self.assertEqual(detect_scheme("I need a Tax Saver for 80c"), "elss")
        
    def test_flexicap_variations(self):
        self.assertEqual(detect_scheme("FLEXICAP fund details"), "flexicap")
        self.assertEqual(detect_scheme("what is a flexible fund"), "flexicap")

if __name__ == "__main__":
    unittest.main()
