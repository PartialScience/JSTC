"""
Converters between the domain GeometricMatrixBundle and its schema.
"""
from app.simulation.facade.matrices import GeometricMatrixBundle
from app.schemas.matrix_schemas import MatrixBundleSchema


def bundle_to_schema(bundle: GeometricMatrixBundle) -> MatrixBundleSchema:
    return MatrixBundleSchema(
        nodal_capacitance=[list(row) for row in bundle.nodal_capacitance],
        topload_charge=list(bundle.topload_charge),
        inductance=[list(row) for row in bundle.inductance],
        coupling=list(bundle.coupling),
        discretization_order=bundle.discretization_order,
        geometry_fingerprint=bundle.geometry_fingerprint,
    )


def bundle_from_schema(schema: MatrixBundleSchema) -> GeometricMatrixBundle:
    return GeometricMatrixBundle(
        nodal_capacitance=tuple(tuple(row) for row in schema.nodal_capacitance),
        topload_charge=tuple(schema.topload_charge),
        inductance=tuple(tuple(row) for row in schema.inductance),
        coupling=tuple(schema.coupling),
        discretization_order=schema.discretization_order,
        geometry_fingerprint=schema.geometry_fingerprint,
    )
