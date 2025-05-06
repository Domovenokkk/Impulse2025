import xml.etree.ElementTree as ET
import json
from collections import defaultdict
import os

def ensure_output_dir():
    if not os.path.exists('out'):
        os.makedirs('out')

def parse_xml_model(xml_file):
    tree = ET.parse(os.path.join('input', xml_file))
    root = tree.getroot()
    
    classes = {}
    aggregations = []
    
    for elem in root:
        if elem.tag == 'Class':
            class_name = elem.attrib['name']
            is_root = elem.attrib.get('isRoot', 'false').lower() == 'true'
            documentation = elem.attrib.get('documentation', '')
            
            attributes = []
            for attr in elem.findall('Attribute'):
                attributes.append({
                    'name': attr.attrib['name'],
                    'type': attr.attrib['type']
                })
            
            classes[class_name] = {
                'name': class_name,
                'isRoot': is_root,
                'documentation': documentation,
                'attributes': attributes,
                'children': []
            }
        
        elif elem.tag == 'Aggregation':
            aggregations.append({
                'source': elem.attrib['source'],
                'target': elem.attrib['target'],
                'sourceMultiplicity': elem.attrib['sourceMultiplicity'],
                'targetMultiplicity': elem.attrib['targetMultiplicity']
            })
    
    for agg in aggregations:
        source = agg['source']
        target = agg['target']
        
        if target in classes:
            multiplicity = agg['sourceMultiplicity']
            if '..' in multiplicity:
                min_val, max_val = multiplicity.split('..')
            else:
                min_val = max_val = multiplicity
            
            classes[target]['children'].append({
                'name': source,
                'type': 'class',
                'min': min_val,
                'max': max_val
            })
    
    return classes

def generate_config_xml(classes):
    def build_xml_element(class_name, indent=0):
        class_info = classes[class_name]
        indent_str = '    ' * indent
        element_lines = []
        
        element_lines.append(f"{indent_str}<{class_name}>")
        
        for attr in class_info['attributes']:
            element_lines.append(f"{indent_str}    <{attr['name']}>{attr['type']}</{attr['name']}>")
        
        for child in class_info['children']:
            child_name = child['name']
            child_lines = build_xml_element(child_name, indent + 1)
            element_lines.extend(child_lines)
        
        element_lines.append(f"{indent_str}</{class_name}>")
        
        return element_lines
    
    root_class = None
    for class_name, class_info in classes.items():
        if class_info['isRoot']:
            root_class = class_name
            break
    
    if not root_class:
        raise ValueError("No root class found in the model")
    
    xml_lines = build_xml_element(root_class)
    return '\n'.join(xml_lines)

def generate_meta_json(classes):
    meta_data = []
    
    for class_name, class_info in classes.items():
        class_entry = {
            'class': class_name,
            'documentation': class_info['documentation'],
            'isRoot': class_info['isRoot'],
            'parameters': []
        }
        
        for attr in class_info['attributes']:
            class_entry['parameters'].append({
                'name': attr['name'],
                'type': attr['type']
            })
        
        for child in class_info['children']:
            class_entry['parameters'].append({
                'name': child['name'],
                'type': 'class'
            })
            
            if 'min' in child and 'max' in child:
                for param in class_entry['parameters']:
                    if param['name'] == child['name']:
                        param['min'] = child['min']
                        param['max'] = child['max']
                        break
        
        meta_data.append(class_entry)
    
    return json.dumps(meta_data, indent=4)

def compare_configs(config1, config2):
    delta = {
        'additions': [],
        'deletions': [],
        'updates': []
    }
    
    for key in config1:
        if key not in config2:
            delta['deletions'].append(key)
    
    for key in config2:
        if key not in config1:
            delta['additions'].append({
                'key': key,
                'value': config2[key]
            })
        elif config1[key] != config2[key]:
            delta['updates'].append({
                'key': key,
                'from': config1[key],
                'to': config2[key]
            })
    
    return delta

def apply_delta(config, delta):
    new_config = config.copy()
    
    for key in delta['deletions']:
        if key in new_config:
            del new_config[key]
    
    for update in delta['updates']:
        key = update['key']
        if key in new_config:
            new_config[key] = update['to']
    
    for addition in delta['additions']:
        new_config[addition['key']] = addition['value']
    
    return new_config

def main():
    ensure_output_dir()
    
    classes = parse_xml_model('impulse_test_input.xml')
    
    config_xml = generate_config_xml(classes)
    with open(os.path.join('out', 'config.xml'), 'w') as f:
        f.write(config_xml)
    
    meta_json = generate_meta_json(classes)
    with open(os.path.join('out', 'meta.json'), 'w') as f:
        f.write(meta_json)
    
    with open(os.path.join('input', 'config.json'), 'r') as f:
        config = json.load(f)
    
    with open(os.path.join('input', 'patched_config.json'), 'r') as f:
        patched_config = json.load(f)
    
    delta = compare_configs(config, patched_config)
    with open(os.path.join('out', 'delta.json'), 'w') as f:
        json.dump(delta, f, indent=4)

    res_patched_config = apply_delta(config, delta)
    with open(os.path.join('out', 'res_patched_config.json'), 'w') as f:
        json.dump(res_patched_config, f, indent=4)

if __name__ == '__main__':
    main()