"""JSON Schema utilities for structured outputs."""

from typing import Any, Type

from pydantic import BaseModel


def pydantic_to_json_schema(model: Type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model to a JSON Schema for structured outputs.

    This generates a JSON Schema that can be used with Azure OpenAI's
    structured outputs feature (response_format with json_schema).

    Args:
        model: A Pydantic model class

    Returns:
        JSON Schema dictionary compatible with OpenAI's structured outputs
    """
    # Get the JSON schema from Pydantic
    schema = model.model_json_schema()

    # OpenAI structured outputs require specific formatting
    # Remove $defs and inline definitions if needed for simpler schemas
    # For complex schemas, we keep $defs as OpenAI supports them

    return schema


def make_strict_schema(
    schema: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    """Wrap a JSON Schema for use with OpenAI's strict structured outputs.

    Args:
        schema: The JSON Schema dictionary
        name: Name for the schema

    Returns:
        Formatted schema dict for response_format parameter
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


def extract_json_schema_for_structured_output(
    model: Type[BaseModel],
) -> dict[str, Any]:
    """Extract and prepare a Pydantic model's schema for structured output.

    This handles the nuances of converting Pydantic v2 schemas to what
    OpenAI's API expects for structured outputs.

    Args:
        model: A Pydantic model class

    Returns:
        JSON Schema ready for OpenAI structured outputs
    """
    schema = model.model_json_schema()

    # Ensure additionalProperties is set appropriately for strict mode
    # OpenAI strict mode requires additionalProperties: false on objects
    _set_additional_properties_false(schema)
    
    # Fix the required array for strict mode
    # Azure OpenAI strict mode requires ALL properties to be in required array
    _fix_required_for_strict_mode(schema)

    return schema


def _fix_required_for_strict_mode(schema: dict[str, Any]) -> None:
    """Ensure all properties are in the required array for strict mode.
    
    Azure OpenAI's strict mode requires that all properties be listed in
    the required array, even if they have default values.
    """
    if not isinstance(schema, dict):
        return
    
    # Fix required array for this level
    if schema.get("type") == "object" and "properties" in schema:
        # Get all property names
        all_props = list(schema["properties"].keys())
        
        # Ensure required array includes all properties
        if "required" not in schema:
            schema["required"] = all_props
        else:
            # Add any missing properties to required
            existing_required = set(schema["required"])
            for prop in all_props:
                if prop not in existing_required:
                    schema["required"].append(prop)
    
    # Recursively process nested schemas
    if "properties" in schema:
        for prop_schema in schema["properties"].values():
            _fix_required_for_strict_mode(prop_schema)
    
    # Process $defs
    if "$defs" in schema:
        for def_schema in schema["$defs"].values():
            _fix_required_for_strict_mode(def_schema)
    
    # Process items for arrays
    if "items" in schema:
        _fix_required_for_strict_mode(schema["items"])
    
    # Process anyOf/oneOf/allOf
    for key in ["anyOf", "oneOf", "allOf"]:
        if key in schema:
            for sub_schema in schema[key]:
                _fix_required_for_strict_mode(sub_schema)


def _set_additional_properties_false(schema: dict[str, Any]) -> None:
    """Recursively set additionalProperties to false for strict mode.

    OpenAI's strict structured outputs require all object types to have
    additionalProperties set to false.
    """
    if not isinstance(schema, dict):
        return

    # Set additionalProperties for object types
    if schema.get("type") == "object":
        if "additionalProperties" not in schema:
            schema["additionalProperties"] = False

    # Process properties if present
    if "properties" in schema:
        for prop_schema in schema["properties"].values():
            _set_additional_properties_false(prop_schema)

    # Process $defs if present
    if "$defs" in schema:
        for def_schema in schema["$defs"].values():
            _set_additional_properties_false(def_schema)

    # Process items for arrays
    if "items" in schema:
        _set_additional_properties_false(schema["items"])

    # Process anyOf/oneOf/allOf
    for key in ["anyOf", "oneOf", "allOf"]:
        if key in schema:
            for sub_schema in schema[key]:
                _set_additional_properties_false(sub_schema)
