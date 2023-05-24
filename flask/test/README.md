# The first attempt at automated testing for lrpi_player

Let's shorten that development feedback loop and unlock refactoring power!

Note - for these tests to pass successfully, you must run:

```
pytest
```

...from THIS directory. Additionally, you must have VLC installed on the host running the tests.

Caveats:

- only tested on Ubuntu/x86_64 machine
- until now... ?

to run specific tests:

```
pytest -vv -k "test_play_pause"
```
