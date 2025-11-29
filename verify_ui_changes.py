import sys
import os
import tkinter

# Mock tkinter to avoid display errors during import if possible
# But customtkinter imports tkinter.
# In this environment, let's see if we can import without display.

try:
    print("Verifying ppmonk.core.visualizer...")
    from ppmonk.core.visualizer import TimelineDataCollector
    t = TimelineDataCollector()
    print(f"Groups: {len(t.groups)}")
    assert len(t.groups) == 5
    print("Visualizer OK.")

    # We can inspect the file content for specific strings to verify changes

    with open('ppmonk/core/visualizer.py', 'r') as f:
        content = f.read()
        assert "主要填充 (Major Filler)" in content
        assert "'Zenith': {'group': 1" in content

    with open('ppmonk/ui/sandbox_ui.py', 'r') as f:
        content = f.read()
        assert "查看详细时间轴" in content
        assert "collector.log_cast" in content
        assert "cast_time = 0.0" in content # Zenith check

    with open('ui.py', 'r') as f:
        content = f.read()
        assert "self.active_talents_list = ['1-1'" in content
        assert '"Haste": "急速"' in content

    with open('ppmonk/ui/talent_ui.py', 'r') as f:
        content = f.read()
        assert '"label": "TEB\\nBuff"' in content
        assert '"max_rank": 2' in content
        assert 'text="应用 & 关闭"' in content

    print("File Content Verification OK.")

except Exception as e:
    print(f"Verification Failed: {e}")
    sys.exit(1)

print("All verifications passed.")
