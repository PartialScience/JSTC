"""
Demo script showing how to visualize geometric regions.

Run this script to generate example visualizations of circles, polygons, and rectangles.
Displays plots in interactive windows.
"""
from app.geometry import Circle, Polygon, Rectangle, visualize_region
import matplotlib.pyplot as plt
import math 


def demo_circle():
    """Demonstrate circle visualization."""
    print("Creating circle visualization...")
    
    # Create a circle
    circle = Circle(center=(0, 0), radius=5.0)
    
    # Visualize circle
    fig = visualize_region(circle, title="Circle Region")


def demo_polygon():
    """Demonstrate polygon visualization."""
    print("\nCreating polygon visualization...")
        
    # Generate star vertices (alternating between outer and inner radius)
    num_points = 5
    outer_radius = 3.0
    inner_radius = 1.2
    star_vertices = []
    
    for i in range(num_points * 2):
        angle = i * math.pi / num_points - math.pi / 2  # Start from top
        radius = outer_radius if i % 2 == 0 else inner_radius
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        star_vertices.append((x, y))
    
    star = Polygon(vertices=tuple(star_vertices))
    
    # Visualize the star
    fig = visualize_region(star, title="5-Pointed Star")


def demo_rectangle():
    """Demonstrate rectangle visualization."""
    print("\nCreating rectangle visualization...")
    
    # Axis-aligned rectangle
    rect_aligned = Rectangle(vertices=((0, 0), (3, 0), (3, 2), (0, 2)))
    
    # Rotated rectangle
    angle = math.pi / 6  # 30 degrees
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    width, height = 3, 2
    
    # Rotate rectangle around origin
    vertices_rotated = (
        (0, 0),
        (width * cos_a, width * sin_a),
        (width * cos_a - height * sin_a, width * sin_a + height * cos_a),
        (-height * sin_a, height * cos_a)
    )
    rect_rotated = Rectangle(vertices=vertices_rotated)
    
    # Visualize both rectangles
    fig = visualize_region(
        [rect_aligned, rect_rotated],
        colors=['lightblue', 'lightcoral'],
        labels=['Axis-Aligned', 'Rotated 30°'],
        title="Rectangle Comparison"
    )


def demo_multiple_regions():
    """Demonstrate plotting multiple regions together."""
    print("\nCreating multi-region visualization...")
    
    circle = Circle(center=(0, 0), radius=3.0)
    square = Polygon(vertices=((-2, -2), (2, -2), (2, 2), (-2, 2)))
    triangle = Polygon(vertices=((-1, -3), (1, -3), (0, -1)))
    
    fig = visualize_region(
        [circle, square, triangle],
        colors=['lightblue', 'lightgreen', 'lightcoral'],
        labels=['Circle', 'Square', 'Triangle'],
        title="Multiple Overlapping Regions"
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Geometric Region Visualization Demo")
    print("=" * 60)
    print("\nClose each plot window to see the next visualization...")
    
    demo_circle()
    demo_polygon()
    demo_rectangle()
    demo_multiple_regions()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    
    # Display the plots
    plt.show()
