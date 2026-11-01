import os
import tempfile

# Keep tests away from your real snkrs_data.db
os.environ.setdefault("SNKRS_DB_PATH", os.path.join(tempfile.mkdtemp(), "snkrs_test.db"))
