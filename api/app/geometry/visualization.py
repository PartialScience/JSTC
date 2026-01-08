"""
Visualization utilities for geometric regions.

This module provides functions to visualize geometric shapes
Works with any GeometricRegion subclass 
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np
from typing import List, Optional, Tuple, Union
from .regions import GeometricRegion


def _get_region_bounds(region: GeometricRegion) -> Tuple[float, float, float, float]:
    """
    Estimate bounds of a region by checking various attributes.
    
    Args:
        region: The geometric region
        
    Returns:
        Tuple of (x_min, x_max, y_min, y_max)
    """
    # Try to get bounds from common attributes
    if hasattr(region, 'center') and hasattr(region, 'radius'):
        # Circle-like
        x_min = region.center[0] - region.radius
        x_max = region.center[0] + region.radius
        y_min = region.center[1] - region.radius
        y_max = region.center[1] + region.radius
    elif hasattr(region, 'vertices'):
        # Polygon-like
        vertices = np.array(region.vertices)
        x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
        y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
    else:
        # Default bounds
        x_min, x_max = -10, 10
        y_min, y_max = -10, 10
    
    return x_min, x_max, y_min, y_max


def visualize_region(
    regions: Union[GeometricRegion, List[GeometricRegion]],
    colors: Optional[Union[str, List[str]]] = None,
    labels: Optional[Union[str, List[str]]] = None,
    x_range: Optional[Tuple[float, float]] = None,
    y_range: Optional[Tuple[float, float]] = None,
    resolution: int = 150,
    figsize: Tuple[int, int] = (10, 10),
    title: Optional[str] = None
) -> plt.Figure:
    """
    Visualize one or more geometric regions using heatmap rendering.
    
    Works with any GeometricRegion subclass by testing point containment on a grid.
    
    Args:
        regions: A single GeometricRegion or list of regions to visualize
        colors: Color(s) for region(s). Single color or list matching regions.
        labels: Label(s) for region(s). Single label or list matching regions.
        x_range: Optional (min, max) for x axis, auto-detected if None
        y_range: Optional (min, max) for y axis, auto-detected if None
        resolution: Grid resolution for rendering (higher = smoother but slower)
        figsize: Figure size (width, height)
        title: Optional title for the plot
        
    Returns:
        The matplotlib figure object
        
    Examples:
        >>> # Single region
        >>> circle = Circle(center=[0, 0], radius=5)
        >>> visualize_region(circle)
        
        >>> # Multiple regions
        >>> regions = [circle, square, triangle]
        >>> visualize_region(regions, colors=['blue', 'green', 'red'],
        ...                  labels=['Circle', 'Square', 'Triangle'])
    """
    # Normalize inputs to lists
    if not isinstance(regions, list):
        regions = [regions]
    
    num_regions = len(regions)
    
    # Set default colors
    if colors is None:
        default_colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
        colors = [default_colors[i % len(default_colors)] for i in range(num_regions)]
    elif isinstance(colors, str):
        colors = [colors]
    
    # Set default labels
    if labels is None:
        labels = [region.__class__.__name__ for region in regions]
    elif isinstance(labels, str):
        labels = [labels]
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Determine bounds from all regions if not provided
    if x_range is None or y_range is None:
        all_bounds = [_get_region_bounds(region) for region in regions]
        x_min = min(bounds[0] for bounds in all_bounds)
        x_max = max(bounds[1] for bounds in all_bounds)
        y_min = min(bounds[2] for bounds in all_bounds)
        y_max = max(bounds[3] for bounds in all_bounds)
        
        margin = max(x_max - x_min, y_max - y_min) * 0.15
        if x_range is None:
            x_range = (x_min - margin, x_max + margin)
        if y_range is None:
            y_range = (y_min - margin, y_max + margin)
    
    # Create shared grid
    x = np.linspace(x_range[0], x_range[1], resolution)
    y = np.linspace(y_range[0], y_range[1], resolution)
    xx, yy = np.meshgrid(x, y)
    
    # Plot each region
    legend_handles = []
    for region, color, label in zip(regions, colors, labels):
        # Test containment
        containment = np.zeros_like(xx)
        for i in range(resolution):
            for j in range(resolution):
                point = [xx[i, j], yy[i, j]]
                containment[i, j] = 1.0 if region.contains(point) else 0.0
        
        # Plot filled region
        ax.contourf(xx, yy, containment, levels=[0.5, 1], colors=[color], alpha=0.5)
        
        # Plot boundary
        ax.contour(xx, yy, containment, levels=[0.5], colors=[color], linewidths=2.5)
        
        # Add to legend
        legend_handles.append(Line2D([0], [0], color=color, linewidth=2.5, label=label))
    
    # Configure plot
    ax.set_xlim(x_range)
    ax.set_ylim(y_range)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linewidth=0.5)
    ax.axvline(x=0, color='k', linewidth=0.5)
    ax.legend(handles=legend_handles, loc='best')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    elif num_regions == 1:
        ax.set_title(f'{labels[0]} Visualization', fontsize=14, fontweight='bold')
    else:
        ax.set_title('Region Visualization', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    return fig
