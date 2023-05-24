# Test plan for pairing mode
# might be worth testing master and slave separately
# and basing everything on time
#
# key - need to somehow force 'paired' to true
# Can we do some network call mocking? Here's hoping!
#
# if not therefore - might be worth testing Player.py class in isolation
# alas, network calls are still made
#
# for master - set to isMaster
# send play command
# play should begin N seconds later, not before
#
# send pause command
# query status
# track should be paused N seconds later
#
#
# for slave - set to isSlave
# receive play command
# play should begin N seconds later, not before
# query status - should be Playing, should be within < 10ms?
#
# send pause command
# query status
# track should be paused N seconds alter
#
# For full e2e test, Party mode testing should be a script that runs
# against two real rpis
# Could be against player api endpoints
# might also be a Cypress (or Playwright?) test with a real frontend
# - that would also be a nice way to ensure that the 'pair' button at the
# - top of the app sticks properly when paired
# ooh, complex


class TestPartyPairingMode:
    def test_winston_orwell(self):
        assert 2 + 2 != 5
