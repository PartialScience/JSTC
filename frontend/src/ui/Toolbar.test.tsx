import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { defaultCoil } from '../domain/coil';
import { useEditorStore } from '../state/store';
import { Toolbar } from './Toolbar';

const reset = () =>
  useEditorStore.setState({
    coil: defaultCoil(),
    selection: [{ kind: 'secondary' }],
    tool: 'pan',
    placementShape: 'circle',
    revision: 0,
    past: [],
    future: [],
  });

const noop = () => {};
const renderToolbar = () =>
  render(<Toolbar onRun={noop} running={false} dirty={false} hasRun={false} />);

describe('Toolbar placement dropdown', () => {
  beforeEach(reset);
  afterEach(cleanup);

  it('has a one-shot Select button that toggles select mode on and off', () => {
    renderToolbar();
    const btn = screen.getByTestId('tool-select');
    expect(useEditorStore.getState().tool).toBe('pan');
    fireEvent.click(btn);
    expect(useEditorStore.getState().tool).toBe('select');
    // Clicking again toggles back to the pan default.
    fireEvent.click(btn);
    expect(useEditorStore.getState().tool).toBe('pan');
  });

  it('grays out the primary and secondary buttons when they exist', () => {
    renderToolbar();
    // The default coil has both, and each is a singleton.
    expect(screen.getByTestId('tool-secondary')).toBeDisabled();
    expect(screen.getByTestId('tool-primary')).toBeDisabled();
  });

  it('shows no geometry menu until the placement button is clicked', () => {
    renderToolbar();
    expect(screen.queryByTestId('shape-menu-topload')).toBeNull();
    expect(screen.queryByTestId('shape-menu-ground')).toBeNull();
  });

  it('opens the geometry menu from the button and arms the chosen shape', () => {
    renderToolbar();
    fireEvent.click(screen.getByTestId('tool-topload'));
    expect(screen.getByTestId('shape-menu-topload')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('shape-topload-rectangle'));
    // Choosing closes the menu and arms the tool with that geometry.
    expect(screen.queryByTestId('shape-menu-topload')).toBeNull();
    const s = useEditorStore.getState();
    expect(s.tool).toBe('topload');
    expect(s.placementShape).toBe('rectangle');
  });

  it('reflects the armed geometry in the active button label', () => {
    renderToolbar();
    fireEvent.click(screen.getByTestId('tool-ground'));
    fireEvent.click(screen.getByTestId('shape-ground-polygon'));
    expect(screen.getByTestId('tool-ground')).toHaveTextContent('Polygon');
  });

  it('clicking the backdrop closes the menu without arming placement', () => {
    renderToolbar();
    fireEvent.click(screen.getByTestId('tool-topload'));
    // The backdrop is the only element with this class while the menu is open.
    fireEvent.click(document.querySelector('.dropdown-backdrop')!);
    expect(screen.queryByTestId('shape-menu-topload')).toBeNull();
    expect(useEditorStore.getState().tool).toBe('pan');
  });
});
