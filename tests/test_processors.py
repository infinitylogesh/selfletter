import json

import pytest
from unittest.mock import MagicMock, patch

from selfletter.processors.arxiv import ArxivProcessor
from selfletter.processors.huggingface import HuggingFaceProcessor
from selfletter.processors.youtube import YouTubeProcessor
from selfletter.processors.article import ArticleProcessor

@pytest.fixture
def config():
    return {
        "openai_api_key": "test",
        "openai_model": "test",
        "openai_endpoint": "test",
        "summary_prompt": "test",
        "max_chars": 1000,
        "user_agent": "test-bot"
    }

def test_arxiv_processor_can_handle(config):
    processor = ArxivProcessor(**config)
    assert processor.can_handle("https://arxiv.org/abs/2512.18552") is True
    assert processor.can_handle("https://arxiv.org/pdf/2512.18552.pdf") is True
    assert processor.can_handle("https://arxiv.org/html/2512.18552") is True
    assert processor.can_handle("arXiv:2512.18552") is True
    assert processor.can_handle("https://google.com") is False

def test_arxiv_id_extraction(config):
    processor = ArxivProcessor(**config)
    assert processor._extract_arxiv_id("https://arxiv.org/abs/2512.18552") == "2512.18552"
    assert processor._extract_arxiv_id("https://arxiv.org/pdf/2301.12345v1.pdf") == "2301.12345"
    assert processor._extract_arxiv_id("arXiv:2101.00001") == "2101.00001"

def test_huggingface_processor_can_handle(config):
    processor = HuggingFaceProcessor(**config)
    assert processor.can_handle("https://huggingface.co/papers/2512.18099") is True
    assert processor.can_handle("https://huggingface.co/papers/2512.18099?utm_source=test") is True
    # HuggingFaceProcessor's can_handle specifically only looks for HF links
    assert processor.can_handle("https://arxiv.org/abs/2512.18099") is False 
    assert processor.can_handle("https://google.com") is False

def test_huggingface_id_extraction(config):
    processor = HuggingFaceProcessor(**config)
    assert processor._extract_hf_arxiv_id("https://huggingface.co/papers/2512.18099") == "2512.18099"
    assert processor._extract_hf_arxiv_id("https://huggingface.co/papers/2303.12345?query=1") == "2303.12345"

def test_youtube_processor_can_handle(config):
    processor = YouTubeProcessor(**config)
    assert processor.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert processor.can_handle("https://youtu.be/dQw4w9WgXcQ") is True
    assert processor.can_handle("https://youtube.com/embed/dQw4w9WgXcQ") is True
    assert processor.can_handle("https://google.com") is False

def test_youtube_id_extraction(config):
    processor = YouTubeProcessor(**config)
    assert processor._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert processor._extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_article_processor_can_handle(config):
    processor = ArticleProcessor(**config)
    assert processor.can_handle("https://any-website.com/article") is True
    assert processor.can_handle("https://google.com") is True


def _summary_response(content, finish_reason="stop"):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    return response


@patch("selfletter.processors.base.requests.post")
def test_summary_retries_empty_responses_with_less_content(mock_post, config):
    config.update(summary_prompt="{content}", max_chars=80000)
    processor = ArticleProcessor(**config)
    mock_post.side_effect = [
        _summary_response(""),
        _summary_response("  "),
        _summary_response("final summary"),
    ]

    summary = processor.summarize("Title", "https://example.com", "x" * 100000)

    assert summary == "final summary"
    assert mock_post.call_count == 3
    prompt_lengths = [
        len(json.loads(call.kwargs["data"])["messages"][0]["content"])
        for call in mock_post.call_args_list
    ]
    assert prompt_lengths == [80000, 40000, 20000]


@patch("selfletter.processors.base.requests.post")
def test_summary_raises_after_all_empty_responses(mock_post, config):
    config.update(summary_prompt="{content}", max_chars=80000)
    processor = ArticleProcessor(**config)
    mock_post.side_effect = [
        _summary_response(""),
        _summary_response(""),
        _summary_response(""),
    ]

    with pytest.raises(RuntimeError, match="no summary after 3 attempts"):
        processor.summarize("Title", "https://example.com", "x" * 100000)
