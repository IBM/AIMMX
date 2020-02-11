"""
    Utility functions specific to caffe2
"""
import json

def value_json_to_schema(schema_contents):
    try:
        value_info = json.loads(schema_contents)
    except json.decoder.JSONDecodeError as e:
        # This is to catch the case where value_info.json is stored in LFS
        print(e)
        return None
    #print(value_info)
    dimensions = None
    for k,v in value_info.items():
        if "data" in k:
            dimensions = v[1]
    input_schema = None
    if dimensions:
        input_schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$id": "input_definition_data_schema.json",
            "id": "input_definition_data_schema.json",
            "title": "Input Data Schema from value_info.json",
            "type": "object",
            "required": ["input"],
            "properties": {
                "input": {
                  "description": "Images",
                  "dimensions": dimensions
                }
            }
        }
    return input_schema
