/**
 * The top bar: whole-session actions that sit above the editor. Load the demo
 * coil or a blank one, or import/export a session file (`.jstc`). Import and
 * export round-trip the *whole* session — geometry plus the last computed
 * outputs and their cached matrix bundle — so a reloaded coil shows results
 * without recomputing. All loads go through the store's `loadSession`, so each
 * is a single undo step and sets the stale/up-to-date state correctly.
 */
import { useRef, useState } from 'react';

import { blankCoil, defaultCoil } from '../domain/coil';
import { useEditorStore } from '../state/store';
import {
  CoilFileError,
  exportFilename,
  parseSession,
  serializeSession,
} from '../state/coilFile';

type Notice = { kind: 'error' | 'info'; text: string } | null;

/** `dirty` (results stale vs. the coil) is derived by the analysis hook, so
 *  it is passed in — it becomes the exported session's `stale` flag. */
export function TopBar({ dirty }: { dirty: boolean }) {
  const loadSession = useEditorStore((s) => s.loadSession);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const loadDemo = () => {
    loadSession({ coil: defaultCoil(), analysis: null, stale: false });
    setNotice(null);
  };

  const loadNew = () => {
    loadSession({ coil: blankCoil(), analysis: null, stale: false });
    setNotice(null);
  };

  const exportSession = () => {
    const { coil, analysis } = useEditorStore.getState();
    const text = serializeSession({ coil, analysis, stale: dirty });
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = exportFilename();
    a.click();
    URL.revokeObjectURL(url);
  };

  const pickFile = () => fileInput.current?.click();

  const onFileChosen = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so choosing the same file again re-triggers onChange.
    e.target.value = '';
    if (!file) return;
    try {
      const session = parseSession(await file.text());
      loadSession(session);
      setNotice(
        session.warnings.length
          ? { kind: 'info', text: session.warnings.join(' ') }
          : null,
      );
    } catch (err) {
      const text =
        err instanceof CoilFileError
          ? err.message
          : `Could not import "${file.name}".`;
      setNotice({ kind: 'error', text });
    }
  };

  return (
    <div className="topbar" data-testid="topbar">
      <div className="topbar-brand">JSTC</div>
      <div className="topbar-group">
        <button type="button" className="topbar-btn" data-testid="topbar-demo" onClick={loadDemo}>
          Demo coil
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-new" onClick={loadNew}>
          New coil
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-import" onClick={pickFile}>
          Import…
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-export" onClick={exportSession}>
          Export
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".jstc,.json,application/json"
          data-testid="topbar-file-input"
          style={{ display: 'none' }}
          onChange={onFileChosen}
        />
      </div>

      {notice && (
        <div
          className={notice.kind === 'error' ? 'topbar-notice error' : 'topbar-notice'}
          data-testid="topbar-notice"
          role={notice.kind === 'error' ? 'alert' : 'status'}
        >
          <span>{notice.text}</span>
          <button
            type="button"
            className="topbar-notice-dismiss"
            aria-label="Dismiss"
            onClick={() => setNotice(null)}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
