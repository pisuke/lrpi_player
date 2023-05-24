# The first attempt at automated testing for lrpi_player

Let's shorten that development feedback loop and unlock refactoring power!

Note - for these tests to pass successfully, you must run:

```
pytest
```

...from THIS directory. Additionally, you must have VLC installed on the host running the tests.

Caveats:

- These tests only run on Rpi3 with omxplayer installed
- Best to run them inside the docker container (which makes NOT including the tests inside the container difficult, hm)
- Also, `pip3 install pytest` if the `pytest` command isn't found
- the `media_base_path` var in settings.json needs thinking about in a repeatable testing context...
  - Maybe symlinks are the way to go here?

to run specific tests:

```
pytest -vv -k "test_play_pause"
```
