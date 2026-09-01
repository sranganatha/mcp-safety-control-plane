import contextlib
import io
import unittest

from mcp_control_plane.demo import run_demo


class DemoTest(unittest.IsolatedAsyncioTestCase):
    async def test_complete_demo(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            await run_demo()

        self.assertEqual(7, output.getvalue().count("PASS "))
        self.assertNotIn("demo-eng-key", output.getvalue())
        self.assertNotIn("demo-sup-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
