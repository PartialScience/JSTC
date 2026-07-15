/**
 * The left panel shown in a field view: sinusoidal drive parameters (the
 * operating point the field is computed at) and display options. Replaces
 * the component parameter panel while a field is on screen.
 */
import { useEditorStore } from '../state/store';
import { QuantityField, SelectField } from './fields';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="sidebar-section active">
      <div className="sidebar-section-header">{title}</div>
      <div className="sidebar-section-body">{children}</div>
    </div>
  );
}

export function FieldDrivePanel() {
  const viewMode = useEditorStore((s) => s.viewMode);
  const drive = useEditorStore((s) => s.fieldDrive);
  const display = useEditorStore((s) => s.fieldDisplay);
  const setDrive = useEditorStore((s) => s.setFieldDrive);
  const setDisplay = useEditorStore((s) => s.setFieldDisplay);
  const analysis = useEditorStore((s) => s.analysis);

  const coupled = analysis?.coupled ?? null;
  const secRes = analysis?.secondary.resonant_frequency ?? null;
  const isElectric = viewMode === 'efield';

  const presets: { label: string; hz: number }[] = [];
  if (coupled) {
    presets.push({ label: 'Lower', hz: coupled.split_lower });
    presets.push({ label: 'Upper', hz: coupled.split_upper });
  }
  if (secRes) presets.push({ label: 'f₀', hz: secRes });

  const effective =
    drive.frequencyHz > 0 ? drive.frequencyHz : (coupled?.split_lower ?? secRes ?? 0);

  return (
    <div className="sidebar" data-testid="field-drive-panel">
      <h2 className="sidebar-title">{isElectric ? 'E-field' : 'B-field'} drive</h2>

      <Section title="Operating point">
        <QuantityField
          label="frequency"
          kind="frequency"
          fieldId="drive-frequency"
          defaultUnit="kHz"
          value={effective}
          min={0}
          onCommit={(hz) => setDrive({ frequencyHz: Math.max(0, hz) })}
          testId="drive-frequency"
        />
        {presets.length > 0 && (
          <div className="preset-row" data-testid="drive-presets">
            {presets.map((p) => (
              <button
                key={p.label}
                type="button"
                className="link-btn"
                data-testid={`drive-preset-${p.label}`}
                onClick={() => setDrive({ frequencyHz: p.hz })}
              >
                {p.label} ({(p.hz / 1e3).toFixed(1)} kHz)
              </button>
            ))}
          </div>
        )}
        <QuantityField
          label="primary current"
          kind="current"
          fieldId="drive-current"
          value={drive.primaryCurrent}
          min={0}
          onCommit={(primaryCurrent) => setDrive({ primaryCurrent })}
          testId="drive-current"
        />
      </Section>

      {isElectric && (
        <Section title="Primary reference">
          <SelectField
            label="reference"
            value={drive.referenceMode}
            options={['floating', 'grounded']}
            onChange={(referenceMode) =>
              setDrive({ referenceMode: referenceMode as 'floating' | 'grounded' })
            }
            testId="drive-reference"
          />
          <SelectField
            label="hot end"
            value={drive.hotEnd}
            options={['outer', 'inner']}
            onChange={(hotEnd) => setDrive({ hotEnd: hotEnd as 'inner' | 'outer' })}
            testId="drive-hotend"
          />
        </Section>
      )}

      <Section title="Display">
        <SelectField
          label="color map"
          value={display.colormap}
          options={['intensity', 'potential']}
          onChange={(colormap) =>
            setDisplay({ colormap: colormap as 'intensity' | 'potential' })
          }
          testId="display-colormap"
        />
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={display.showContours}
            data-testid="display-contours"
            onChange={(e) => setDisplay({ showContours: e.target.checked })}
          />
          contours
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={display.showArrows}
            data-testid="display-arrows"
            onChange={(e) => setDisplay({ showArrows: e.target.checked })}
          />
          field vectors
        </label>
      </Section>
    </div>
  );
}
