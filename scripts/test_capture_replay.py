"""Replay capture rejects malformed or truncated source snapshots."""
import json
import unittest

from capture_replay import valid_batch_response, valid_response


class CaptureReplayTests(unittest.TestCase):
    def test_source_validation(self):
        steam = json.dumps({'10': {'success': True, 'data': {'name': 'Game 10'}}}).encode()
        self.assertEqual(valid_response('Steam Store', steam, 10)['10']['data']['name'], 'Game 10')
        with self.assertRaisesRegex(ValueError, 'another game'):
            valid_response('CheapShark', json.dumps([{'steamAppID': '11', 'title': 'Wrong'}]).encode(), 10)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            valid_response('CheapShark', json.dumps([{'steamAppID': '10'}] * 100).encode(), 10)
        rows = [{'steamAppID': '10', 'title': 'Game 10'}, {'steamAppID': '11', 'title': 'Game 11'}]
        self.assertEqual(len(valid_batch_response(json.dumps(rows).encode(), [10, 11])), 2)
        with self.assertRaisesRegex(ValueError, 'another game'):
            valid_batch_response(json.dumps(rows).encode(), [10])


if __name__ == '__main__':
    unittest.main()
