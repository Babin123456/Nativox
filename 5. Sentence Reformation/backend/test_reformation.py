"""
Unit tests for Stage 5: Sentence Reformation & Précis Compression.
"""
import unittest

from app.reformer import clean_disfluencies, reconstruct_english_syntax, reconstruct_sentence
from app.precis import compress_paragraph_to_budget, generate_precis


class TestSentenceReformation(unittest.TestCase):
    def test_clean_disfluencies_removes_fillers_and_duplicates(self):
        raw = "uh basically we we need to like understand neural networks you know"
        cleaned, removed = clean_disfluencies(raw)

        self.assertNotIn("basically", cleaned.lower())
        self.assertNotIn("you know", cleaned.lower())
        self.assertIn("neural networks", cleaned)
        # Verify duplicate "we we" is collapsed to "we"
        self.assertNotIn("we we", cleaned.lower())
        self.assertTrue(len(removed) > 0)

    def test_reconstruct_english_syntax_keyword_sequence(self):
        keywords = "speech recognition machine translation natural language processing"
        reconstructed = reconstruct_english_syntax(keywords)

        self.assertTrue(reconstructed.endswith("."))
        self.assertTrue(reconstructed[0].isupper())
        self.assertIn("speech recognition", reconstructed.lower())

    def test_reconstruct_sentence_end_to_end(self):
        raw = "uh in this video we basically train deep neural network computer vision"
        res = reconstruct_sentence(raw, target_lang="hindi")

        self.assertIn("meaningful_hindi", res)
        self.assertTrue(len(res["meaningful_hindi"]) > 0)
        self.assertTrue(res["cleaned_english"][0].isupper())
        self.assertTrue(res["cleaned_english"].endswith("."))

    def test_reconstruct_from_comma_separated_keywords(self):
        keywords = "machine learning, neural networks, speech recognition"
        res = reconstruct_sentence(keywords, target_lang="hindi")

        self.assertIn("This explores", res["cleaned_english"])
        self.assertIn("मशीन लर्निंग", res["meaningful_hindi"])
        self.assertTrue(len(res["meaningful_hindi"]) > 0)


class TestPrecisCompression(unittest.TestCase):
    def setUp(self):
        self.sample_paragraph = (
            "Welcome back guys, in this particular tutorial today, what we are basically going to do is explore "
            "how deep learning and artificial neural networks actually work under the hood. You know, many people think "
            "that neural networks are like a magic black box, but actually, it is just basic linear algebra, matrix "
            "multiplication, and calculus with gradient descent. We will take a sample dataset of images, write a Python "
            "script using PyTorch, and see how the loss function decreases step by step until the computer learns to "
            "classify cats and dogs accurately."
        )

    def test_precis_ratio_within_35_to_40_percent(self):
        orig_words = len(self.sample_paragraph.split())
        res = generate_precis(self.sample_paragraph, min_ratio=0.35, max_ratio=0.40, target_lang="hindi")

        precis_words = res["precis_word_count"]
        ratio = (precis_words / orig_words) * 100

        # Check that ratio is comfortably in the ~35% - 40% neighborhood
        self.assertGreaterEqual(ratio, 32.0)
        self.assertLessEqual(ratio, 43.0)
        self.assertTrue(len(res["precis_hindi"]) > 0)
        self.assertIn("neural networks", res["precis_english"].lower())


if __name__ == "__main__":
    unittest.main()
