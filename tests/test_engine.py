import asyncio

from conftest import make_engine

def ask(engine, **options):
    return asyncio.run(engine.chat([{"role": "user", "content": "hi"}], **{"temperature": 0.0, "max_tokens": 9, **options}))

def test_the_base_model_loads_once_and_answers():
    engine = make_engine()
    assert ask(engine)["content"] == "hello"
    assert engine.loads == ["m"] and engine.ready


def test_another_replicas_download_makes_this_one_load_again(tmp_path):
    marker = tmp_path / "marker"
    mine, other = make_engine(marker=marker), make_engine(marker=marker)
    ask(mine)
    mine.sync()
    assert mine.ready
    asyncio.run(other.unload())
    mine.sync()
    assert not mine.ready
    ask(mine)
    assert mine.loads == ["m", "m"]


def test_unload_drops_the_models_here():
    engine = make_engine()
    ask(engine)
    asyncio.run(engine.unload())
    assert not engine.ready


def test_thread_count_is_reported_without_configuring_ollama():
    engine = make_engine()
    engine.num_thread = 4
    assert engine.num_thread == 4


def stream(engine):
    async def run():
        return [event async for event in engine.chat_stream([{"role": "user", "content": "hi"}], temperature=0.0, max_tokens=5)]

    return asyncio.run(run())


def test_chat_stream_gives_the_pieces_then_the_stats_with_the_model_and_fallback():
    events = stream(make_engine(reply="one two"))
    assert events[:2] == [("content", "one "), ("content", "two")]
    assert events[2] == ("done", {"prompt_tokens": 3, "completion_tokens": 5, "finish": "stop", "model": "m", "fallback": False})


def test_closing_a_stream_early_stops_the_generation_and_frees_the_slot():
    async def run():
        engine = make_engine(reply="a b c d")
        events = engine.chat_stream([{"role": "user", "content": "hi"}], temperature=0.0, max_tokens=5)
        await anext(events)
        await events.aclose()
        assert engine._base.stopped.is_set()
        return await asyncio.wait_for(engine.chat([{"role": "user", "content": "hi"}], temperature=0.0, max_tokens=5), 2)

    assert asyncio.run(run())["content"] == "a b c d"


def test_generation_changes_when_the_loaded_models_are_dropped():
    engine = make_engine()
    before = engine.generation
    asyncio.run(engine.unload())
    assert engine.generation == before + 1
