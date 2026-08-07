import httpx
import pytest

from agent.fetchers.hf_trending import (
    HFTrendingAdapter,
    HF_MODELS_API,
    HF_DATASETS_API,
)

MOCK_MODELS = [
    {
        "id": "acme/cool-model",
        "likes": 500,
        "downloads": 10000,
        "createdAt": "2026-08-01T12:00:00.000Z",
        "trendingScore": 900,
    },
    {
        "id": "small/obscure-model",
        "likes": 2,
        "downloads": 5,
        "createdAt": "2026-08-02T09:00:00.000Z",
        "trendingScore": 3,
    },
]

MOCK_DATASETS = [
    {
        "id": "acme/big-dataset",
        "description": "A very large curated dataset",
        "likes": 800,
        "downloads": 42000,
        "createdAt": "2026-07-15T08:00:00.000Z",
        "lastModified": "2026-08-03T10:00:00.000Z",
        "trendingScore": 700,
    },
    {
        "id": "small/tiny-dataset",
        "description": "hardly used",
        "likes": 1,
        "downloads": 3,
        "createdAt": "2026-07-01T00:00:00.000Z",
        "lastModified": "2026-07-01T00:00:00.000Z",
        "trendingScore": 1,
    },
]


def _resp(mocker, payload, status_ok=True):
    resp = mocker.MagicMock()
    resp.json.return_value = payload
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
    return resp


def _mock_both(mocker, models=MOCK_MODELS, datasets=MOCK_DATASETS,
               models_ok=True, datasets_ok=True):
    """Patch httpx.get, dispatching on URL to the models vs datasets payload."""

    def side_effect(url, *args, **kwargs):
        if url == HF_MODELS_API:
            return _resp(mocker, models, status_ok=models_ok)
        if url == HF_DATASETS_API:
            return _resp(mocker, datasets, status_ok=datasets_ok)
        raise AssertionError(f"unexpected url: {url}")

    return mocker.patch("httpx.get", side_effect=side_effect)


def test_query_construction_hits_both_endpoints(mocker):
    mock_get = _mock_both(mocker)
    adapter = HFTrendingAdapter(limit=25, min_likes=0)
    adapter.fetch()

    assert mock_get.call_count == 2
    urls = [c.args[0] for c in mock_get.call_args_list]
    assert HF_MODELS_API in urls
    assert HF_DATASETS_API in urls
    for c in mock_get.call_args_list:
        params = c.kwargs["params"]
        assert params["sort"] == "trendingScore"
        assert params["limit"] == 25


def test_mapping_models(mocker):
    _mock_both(mocker, datasets=[])
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    items = adapter.fetch()

    m = [i for i in items if i.url == "https://huggingface.co/acme/cool-model"]
    assert len(m) == 1
    item = m[0]
    assert item.title == "acme/cool-model"
    assert item.body == ""  # model list payload has no description
    assert item.engagement == 500  # likes, not downloads
    assert item.source == "hf-trending"
    assert item.timestamp == "2026-08-01T12:00:00.000Z"


def test_mapping_datasets(mocker):
    _mock_both(mocker, models=[])
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    items = adapter.fetch()

    d = [i for i in items if i.url == "https://huggingface.co/datasets/acme/big-dataset"]
    assert len(d) == 1
    item = d[0]
    assert item.title == "acme/big-dataset"
    assert item.body == "A very large curated dataset"
    assert item.engagement == 800
    assert item.source == "hf-trending"
    # lastModified preferred over createdAt
    assert item.timestamp == "2026-08-03T10:00:00.000Z"


def test_min_likes_threshold_drops_low(mocker):
    _mock_both(mocker)
    adapter = HFTrendingAdapter(limit=10, min_likes=100)
    items = adapter.fetch()

    urls = [i.url for i in items]
    assert "https://huggingface.co/acme/cool-model" in urls
    assert "https://huggingface.co/datasets/acme/big-dataset" in urls
    assert "https://huggingface.co/small/obscure-model" not in urls
    assert "https://huggingface.co/datasets/small/tiny-dataset" not in urls
    assert len(items) == 2


def test_partial_failure_models_down_returns_datasets(mocker):
    _mock_both(mocker, models_ok=False)
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    items = adapter.fetch()

    urls = [i.url for i in items]
    # models endpoint failed (raise_for_status), datasets still returned
    assert not any(u == "https://huggingface.co/acme/cool-model" for u in urls)
    assert "https://huggingface.co/datasets/acme/big-dataset" in urls
    assert len(items) == 2  # both datasets, min_likes=0


def test_partial_failure_datasets_down_returns_models(mocker):
    _mock_both(mocker, datasets_ok=False)
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    items = adapter.fetch()

    urls = [i.url for i in items]
    assert "https://huggingface.co/acme/cool-model" in urls
    assert not any("datasets" in u for u in urls)
    assert len(items) == 2  # both models, min_likes=0


def test_fail_soft_on_httpx_error(mocker):
    mocker.patch("httpx.get", side_effect=httpx.ConnectError("no network"))
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    assert adapter.fetch() == []


def test_fail_soft_on_malformed_payload(mocker):
    _mock_both(mocker, models={"unexpected": "shape"}, datasets={"also": "wrong"})
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    assert adapter.fetch() == []


def test_fail_soft_on_empty_payload(mocker):
    _mock_both(mocker, models=[], datasets=[])
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    assert adapter.fetch() == []


def test_entry_without_id_skipped(mocker):
    _mock_both(
        mocker,
        models=[{"likes": 999, "createdAt": "2026-08-01T00:00:00Z"}],
        datasets=[],
    )
    adapter = HFTrendingAdapter(limit=10, min_likes=0)
    assert adapter.fetch() == []


def test_lookback_days_stored_not_in_params(mocker):
    mock_get = _mock_both(mocker)
    adapter = HFTrendingAdapter(limit=10, min_likes=0, lookback_days=30)
    assert adapter.lookback_days == 30
    adapter.fetch()
    for c in mock_get.call_args_list:
        params = c.kwargs["params"]
        assert "lookback_days" not in params
        assert "days" not in params


def test_name_attribute():
    assert HFTrendingAdapter(limit=10).name == "hf-trending"
