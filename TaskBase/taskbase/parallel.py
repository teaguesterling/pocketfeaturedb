import time
import struct

# TODO: Move to util module
def ensure_all_imap_unordered_results_finish(result, expected=None, wait=0.5):
    just_started = True
    while True:
        try:
            yield next(result)
            just_started = False
        except StopIteration:
            if (hasattr(result, '_length') and result._length is None) \
              or (expected is not None and result._index < expected):
                time.sleep(wait)
            else:
                raise
        except IndexError:
            if not just_started:
                raise
        except struct.error:
            if not just_started:
                raise
