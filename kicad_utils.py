# This is Part B of a project which aims to convert circuit images into editable kicad schematics.
# Part A uses computer vision to create a list of wires and components with their co-ordinates, and their names.
# Part B takes this list and creates a kicad_sch file from it.

# Symbols and components are used synonymously. Examples of symbol/component: resistor, wire, battery, switch, etc

# Kicad_sch file explanation
# (kicad_sch ... ): This is the root element of the schematic file, indicating that it's a KiCad schematic document.
# (version ... ): Specifies the version of the KiCad schematic format.
# (generator "eeschema"): Indicates that the file was generated by 'eeschema', which is KiCad's schematic editor. It can be anything, even "SidYifanOmarNeel"
# (uuid "...."): A universally unique identifier for the schematic.
# (paper "A4"): Defines the paper size for the schematic print layout.
# (lib_symbols ... ): This section contains definitions for all the symbols (components) used in the schematic.
# (wire ... ): Represents a wire connecting different pins in the schematic.
# (symbol ... ): Places an instance of a symbol on the schematic, which references the lib_symbols definition.
# (sheet_instances ... ): Specifies instances of hierarchical sheets within the schematic, if any.
# Notes:
#   kicad_sch file does not store connections between components. On run time, it sees the co-ordinates of the ends of a wire if it is close to the pin of a component then it is considered to be connected.
#   Co-ordinates (x,y):
#       top left corner is (0,0) in kicad_sch and (0,0) in eeschema
#       top right corner is (297.18,0) in kicad_sch and (11700,0) in eeschema
#       bottom left corner is (0,209.55) in kicad_sch and (0,8250) in eeschema
#       bottom right corner is (297.18,209.55) in kicad_sch and (11700,8250) in eeschema
#       Conversion ratio of co-ordinates = eeschema/kicad_sch = 8250/209.55 = 39.3700787402
#       With internal padding, top left corner is (600,600) in eeschema or (15.24,15.24) in kicad_sch

import uuid
import os
import yaml


def read_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


# Path to the configuration file
config_file_path = 'configuration.yaml'

# Read the configuration
config = read_config(config_file_path)

# Get the symbol library path from the configuration and expand the user path
PATH_TO_SYMBOL_LIBRARY = os.path.expanduser(config['symbol_library_path'])


def create_empty_kicad_sch_template():
    file_uuid = f"{uuid.uuid4()}"
    template = f"""(kicad_sch
    (version 20231120)
    (generator "SidYifanOmarNeel")
    (generator_version "8.0")
    (uuid "{file_uuid}")
    (paper "A4")
    (lib_symbols)
    (sheet_instances
        (path "/"
            (page "1")
        )
    )
)"""
    return template

# print all files in the symbol library


def print_all_files_in_symbol_library():
    import os
    for file in os.listdir(PATH_TO_SYMBOL_LIBRARY):
        if file.endswith(".kicad_sym"):
            print(file)


def extract_subsection(content, subsection):
    # subsection = '(symbol "R"'
    # subsection = '(lib_symbols'
    subsection_start = content.find(subsection)
    if subsection_start == -1:
        return None  # Symbol not found

    balance = 0  # Track the balance of parenthesis
    for i in range(subsection_start, len(content)):
        if content[i] == '(':
            balance += 1
        elif content[i] == ')':
            balance -= 1

        if balance == 0:
            subsection_end = i + 1
            return [subsection_start, subsection_end, content[subsection_start:subsection_end]]
    return None

# Extracts string which is the definition symbol template from Device.kicad_sym file


def extract_symbol_definition(lib_id):
    lib_name = lib_id.split(":")[0]  # Eg: Device
    symbol_name = lib_id.split(":")[1]  # Eg: Battery_Cell
    # Import Library Symbols Definitions
    # This file is the reference which defines the properties of each component
    path_to_lib_kicad_sym_file = f"{PATH_TO_SYMBOL_LIBRARY}{lib_name}.kicad_sym"

    # Read the symbol definition from the device file
    with open(path_to_lib_kicad_sym_file, 'r') as file:
        lib_file_content = file.read()

    subsection = extract_subsection(
        lib_file_content, f'(symbol "{symbol_name}"')
    if subsection is not None:
        symbol_def_string = subsection[2]
        symbol_def_string = symbol_def_string.replace(
            f'(symbol "{symbol_name}"', f'(symbol "{lib_id}"')
        return symbol_def_string
    else:
        raise Exception(
            f"Symbol {symbol_name} not found in {path_to_lib_kicad_sym_file}")


def extract_property_value(subsection, property_name):
    property_start = subsection.find(f'(property "{property_name}"')
    if property_start == -1:
        return None  # Property not found

    value_start = subsection.find(
        '"', property_start + len(f'(property "{property_name}"')) + 1
    value_end = subsection.find('"', value_start + 1)
    return subsection[value_start + 1:value_end]


def add_component_to_kicad_sch_file(kicad_sch_file, component_dict):
    # if symbol for component is not lib_symbol, add it
    libSymbols = extract_subsection(kicad_sch_file, '(lib_symbols')
    if libSymbols[2].find(f'component_dict["lib_id"]"') == -1:
        libSymbols_insert_point = libSymbols[0] + len('(lib_symbols')
        kicad_sch_file = kicad_sch_file[:libSymbols_insert_point] + \
            f"\n {extract_symbol_definition(component_dict['lib_id'])} \n " + \
            kicad_sch_file[libSymbols_insert_point:]

    # add symbol string
    curr_lib_id = component_dict["lib_id"]
    # lib_name = component_dict["lib_id"].split(":")[0] #Eg: Device
    # symbol_name = component_dict["lib_id"].split(":")[1] #Eg: Battery_Cell

    # get file uuid to add to instance section in the bottom of the file
    uuid_section = extract_subsection(kicad_sch_file, '(uuid')
    if uuid_section:
        # Extract the UUID value
        start = uuid_section[2].find('"') + 1  # Find the first quotation mark
        # Find the second quotation mark
        end = uuid_section[2].find('"', start)
        uuid_value = uuid_section[2][start:end]

    # get symbol value from lib_symbols
    libSymbols = extract_subsection(kicad_sch_file, '(lib_symbols')
    if libSymbols is None:
        print("lib_symbols not found")
        raise Exception("lib_symbols not found")

    symbol_section = extract_subsection(
        libSymbols[2], f'(symbol "{curr_lib_id}"')
    if symbol_section is None:
        # print("symbol_section? not found")
        raise Exception(f'symbol_section (symbol "{curr_lib_id}" not found')

    description = extract_property_value(symbol_section[2], "Description")

    # get symbol description from lib_symbols
    property_value = extract_property_value(symbol_section[2], "Value")

    # TODO: set "at" of each property value = parsed_x + lib_symbol_property_x
    symbol_instance = f"""
(symbol
        (lib_id "{component_dict["lib_id"]}")
        (at {component_dict["x"]} {component_dict["y"]} {component_dict["angle"]})
        (unit 1)
        (exclude_from_sim no)
        (in_bom yes)
        (on_board yes)
        (dnp no)
        (fields_autoplaced yes)
        (uuid "{uuid.uuid4()}")
        (property "Reference" "{component_dict["reference_name"]}"
            (at {component_dict["x"]} {component_dict["y"]} 0)
            (effects
                (font
                    (size 1.27 1.27)
                )
            )
        )
        (property "Value" "{property_value}"
            (at {component_dict["x"]} {component_dict["y"]} 0)
            (effects
                (font
                    (size 1.27 1.27)
                )
            )
        )
        (property "Footprint" ""
            (at {component_dict["x"]} {component_dict["y"]} 0)
            (effects
                (font
                    (size 1.27 1.27)
                )
                (hide yes)
            )
        )
        (property "Datasheet" "~"
            (at {component_dict["x"]} {component_dict["y"]} 0)
            (effects
                (font
                    (size 1.27 1.27)
                )
                (hide yes)
            )
        )
        (property "Description" "{description}"
            (at {component_dict["x"]} {component_dict["y"]} 0)
            (effects
                (font
                    (size 1.27 1.27)
                )
                (hide yes)
            )
        )
        (instances
            (project "temp_{uuid_value}"
                (path "/{uuid_value}"
                    (reference "{component_dict["reference_name"]}")
                    (unit 1)
                )
            )
        )
    )    
"""

    libSymbols = extract_subsection(kicad_sch_file, '(lib_symbols')
    symbol_insert_point = libSymbols[1] + 1
    # print(f" the value of symbol_insert_point is {symbol_insert_point}")
    kicad_sch_file = kicad_sch_file[:symbol_insert_point] + \
        f"\n {symbol_instance} \n " + kicad_sch_file[symbol_insert_point:]
    # print(kicad_sch_file)
    return kicad_sch_file


def add_wire_to_kicad_sch_file(kicad_sch_file, wire_dict):
    wire_template = f"""(wire
		(pts
			(xy {wire_dict['x']} {wire_dict['y']}) (xy {wire_dict['end_x']} {wire_dict['end_y']})
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{uuid.uuid4()}")
	)"""
    libSymbols = extract_subsection(kicad_sch_file, '(lib_symbols')
    symbol_insert_point = libSymbols[1] + 1
    kicad_sch_file = kicad_sch_file[:symbol_insert_point] + \
        f"\n {wire_template} \n " + kicad_sch_file[symbol_insert_point:]
    return kicad_sch_file


def create_kicad_sch_file(components=None, wires=None):
    if components is None:
        components = []
    if wires is None:
        wires = []

    # create empty kicad_sch file
    temp_kicad_sch_file = create_empty_kicad_sch_template()

    # add each element to kicad_file
    for component in components:
        temp_kicad_sch_file = add_component_to_kicad_sch_file(
            temp_kicad_sch_file, component)

    for wire in wires:
        temp_kicad_sch_file = add_wire_to_kicad_sch_file(
            temp_kicad_sch_file, wire)

    # save temp file
    file_path = f'temp_{uuid.uuid4()}.kicad_sch'
    with open(file_path, 'w') as file:
        file.write(temp_kicad_sch_file)
    print(f"Created file {file_path}")
    return file_path


def modify_kicad_sch_file(file_path, components=None, wires=None):
    """
    Modifies a KiCad schematic file with the given components and wires.

    Args:
        file_path (str): Path to the KiCad schematic file to be modified. If not provided, an exception is raised.
        components (list of dicts, optional): A list of dictionaries representing components to be added to the schematic.
            Each dictionary should contain the keys 'lib_id', 'x', 'y', 'angle', and 'reference_name'.
            Example: {"lib_id": "Device:Ammeter_AC", "x": 133.35, "y": 64.77, "angle": 0, "reference_name": "BT1"}
        wires (list of dicts, optional): A list of dictionaries representing wires to be added to the schematic.
            Each dictionary should contain the keys 'x', 'y', 'end_x', and 'end_y'.
            Example: {"x": 148.59, "y": 77.47, "end_x": 157.48, "end_y": 77.47}

    Returns:
        str: The modified KiCad schematic file content.
    """

    if components is None:
        components = []
    if wires is None:
        wires = []

    # create empty kicad_sch file
    with open(file_path, 'r') as file:
        temp_kicad_sch_file = file.read()

    # add each element to kicad_file
    for component in components:
        temp_kicad_sch_file = add_component_to_kicad_sch_file(
            temp_kicad_sch_file, component)

    for wire in wires:
        temp_kicad_sch_file = add_wire_to_kicad_sch_file(
            temp_kicad_sch_file, wire)

    # save temp file
    with open(file_path, 'w') as file:
        file.write(temp_kicad_sch_file)
    print(f"Modified file {file_path}")
    return temp_kicad_sch_file


def match_libId(raw_libid: str):
    lib_id = raw_libid
    if "resistor" == raw_libid:
        lib_id = "Device:R"
    elif "capacitor" == raw_libid:
        lib_id = "Device:C"
    elif "transistor" == raw_libid:
        lib_id = "Device:R"
    elif "battery" == raw_libid or "cell" == raw_libid:
        lib_id = "Device:Battery"
    elif "led" == raw_libid:
        lib_id = "Device:LED"

    return lib_id
