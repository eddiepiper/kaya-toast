from kaya_toast.collect import collect_from_json
from kaya_toast.config import load_all_config, load_scoring, load_taxonomy, load_voice


def test_config_loads_expected_sections():
    config = load_all_config()

    assert "taxonomy" in config
    assert "scoring" in config
    assert "preferences" in config
    assert "sources" in config
    assert "llm" in config
    assert "pillars" in config
    assert "positioning" in config
    assert "voice" in config
    assert "ai_native_pm_mindset" in config["taxonomy"]["categories"]
    assert config["scoring"]["thresholds"]["post"] == 70


def test_specific_config_helpers_load():
    assert "categories" in load_taxonomy()
    assert "weights" in load_scoring()
    assert "Enterprise AI operator" in load_voice()["preferred_positioning"][0]


def test_voice_config_contains_banned_phrases():
    voice = load_voice()

    assert "AI will change everything" in voice["banned_phrases"]
    assert "No emojis." in voice["style_rules"]


def test_collect_articles_from_json():
    articles = collect_from_json("examples/sample_articles.json")

    assert len(articles) == 8
    assert articles[0].id == "a1"
    assert articles[0].title
