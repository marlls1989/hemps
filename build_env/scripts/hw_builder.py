#!/usr/bin/python
import sys
import math
import os
from yaml_intf import *
from build_utils import *

## @package hw_builder
#This script compiles the hardware part inside the testcase dir
#It also generate the hardware includes hemps.h or hemps.vhd in the include directory inside the testcase

def main():
    
    testcase_name = sys.argv[1]
    
    yaml_r = get_yaml_reader(testcase_name)

    generate_hw_pkg( yaml_r )
    
    #compile_hw
    exit_status = os.system("cd hardware/; make")
    
    if exit_status != 0:
        sys.exit("\nError compiling hardware source code\n");
    

def generate_hw_pkg( yaml_r ):
    
    #Variables from yaml used into this function
    x_mpsoc_dim =       get_mpsoc_x_dim(yaml_r)
    y_mpsoc_dim =       get_mpsoc_y_dim(yaml_r)
    x_cluster_dim =     get_mpsoc_x_dim(yaml_r)
    y_cluster_dim =     get_mpsoc_y_dim(yaml_r)
    #master_location =   get_master_location(yaml_r)
    system_model_desc = get_model_description(yaml_r)

    cluster_list = [] #create_cluster_list(x_mpsoc_dim, y_mpsoc_dim, x_cluster_dim, y_cluster_dim, master_location)
    
    pe_type = []
    #----------- Generates PEs types ----------------
    is_master_list = []
    #Walk over x and y address
    for y in range(0, y_mpsoc_dim):
        
        for x in range(0, x_mpsoc_dim):
            #By default is a slave PE
            master_pe = False
            
            for cluster_obj in cluster_list:
                if x == cluster_obj.master_x and y == cluster_obj.master_y:
                    master_pe = True
                    break
     
            if master_pe == True:
                is_master_list.append(1) # master
            else:
                is_master_list.append(0) # slave
                
    #------------  Updates the include path -----------
    include_dir_path = "include"
    
    #Creates the include path if not exists
    if os.path.exists(include_dir_path) == False:
        os.mkdir(include_dir_path)
    
    
    if system_model_desc == "sc" or system_model_desc == "scmod":
        
        generate_to_systemc(is_master_list, yaml_r )
    
    elif system_model_desc == "vhdl":
       
        generate_to_vhdl(is_master_list, yaml_r )
        


def generate_to_systemc(is_master_list, yaml_r):
   
    #Variables from yaml used into this function
    page_size_KB =      get_page_size_KB(yaml_r)
    memory_size_KB =    get_memory_size_KB(yaml_r)
    repo_size_bytes =   get_repository_size_BYTES(yaml_r)
    x_mpsoc_dim =       get_mpsoc_x_dim(yaml_r)
    y_mpsoc_dim =       get_mpsoc_y_dim(yaml_r)
    app_number =        get_apps_number(yaml_r)
    
    string_pe_type_sc = ""
    
    #Walk over is master list
    for pe_type in is_master_list:
        
        string_pe_type_sc = string_pe_type_sc + str(pe_type) + ", "
    
    #Remove the lost ',' in the string_pe_type_vhdl
    string_pe_type_sc = string_pe_type_sc[0:len(string_pe_type_sc)-2] # 2 because the space, otherelse will be 1
    

    file_lines = []
    #---------------- SYSTEMC SINTAX ------------------
    file_lines.append("#ifndef _HEMPS_PKG_\n")
    file_lines.append("#define _HEMPS_PKG_\n\n")
    
    file_lines.append("#define PAGE_SIZE_BYTES           "+str(page_size_KB*1024)+"\n")
    file_lines.append("#define MEMORY_SIZE_BYTES      "+str(memory_size_KB*1024)+"\n")
    file_lines.append("#define TOTAL_REPO_SIZE_BYTES   "+str(repo_size_bytes)+"\n")
    file_lines.append("#define APP_NUMBER           "+str(app_number)+"\n")
    file_lines.append("#define N_PE_X              "+str(x_mpsoc_dim)+"\n")
    file_lines.append("#define N_PE_Y              "+str(y_mpsoc_dim)+"\n")
    file_lines.append("#define N_PE                "+str(x_mpsoc_dim*y_mpsoc_dim)+"\n\n")
    
    file_lines.append("const int pe_type[N_PE] = {"+string_pe_type_sc+"};\n\n")
    file_lines.append("#endif\n")
    
    #Use this function to create any file into testcase, it automatically only updates the old file if necessary
    writes_file_into_testcase("include/hemps_pkg.h", file_lines)
    

def generate_to_vhdl(is_master_list, yaml_r):
    
    #Variables from yaml used into this function
    page_size_KB =      get_page_size_KB(yaml_r)
    memory_size_KB =    get_memory_size_KB(yaml_r)
    #repo_size_bytes =   get_repository_size_BYTES(yaml_r)
    noc_buffer_size =   get_noc_buffer_size(yaml_r)
    x_mpsoc_dim =       get_mpsoc_x_dim(yaml_r)
    y_mpsoc_dim =       get_mpsoc_y_dim(yaml_r)
    app_number =        get_apps_number(yaml_r)
    simple_soc =        get_simple_soc(yaml_r)
    open_ports =        get_open_ports(yaml_r)
    io_number =         get_io_number(yaml_r)
    apps_list =         get_apps_list(yaml_r)
    
    
    #These lines compute the logical memory addresses used by the mlite to index the pages at the local memory
    page_size_h_index   = int( math.log ( (page_size_KB * 1024),           2 ) - 1 )
    #The ceil is used to support floating point log results
    page_number_h_index = int( math.ceil( math.log ( (memory_size_KB/ page_size_KB) , 2 ) )  + page_size_h_index )
    
    string_pe_type_vhdl = ""
    
    #Walk over is master list
    for pe_type in is_master_list:
        
        if pe_type == 0: #slave
            string_pe_type_vhdl = string_pe_type_vhdl + "\"sla\","
        else:
            string_pe_type_vhdl = string_pe_type_vhdl + "\"mas\","
    
    #Remove the lost ',' in the string_pe_type_vhdl
    string_pe_type_vhdl = string_pe_type_vhdl[0:len(string_pe_type_vhdl)-1]

    open_ports_vector = []
    for i in range(0,x_mpsoc_dim*y_mpsoc_dim):
        open_ports_vector.append("gnd");

    for port in open_ports:
        index = port[1]*x_mpsoc_dim + port[0]
        if port[2] == "N":
            open_ports_vector[index] = "nor"
        if port[2] == "S":
            open_ports_vector[index] = "sou"
        if port[2] == "E":
            open_ports_vector[index] = "eas"
        if port[2] == "W":
            open_ports_vector[index] = "wes"

    if open_ports[0][2] == "N":
        loader_addr = 0xC0000000
    if open_ports[0][2] == "S":
        loader_addr = 0xE0000000
    if open_ports[0][2] == "E":
        loader_addr = 0x80000000
    if open_ports[0][2] == "W":
        loader_addr = 0xA0000000

    loader_addr = loader_addr + (open_ports[0][1] << 8) + open_ports[0][1]


    open_ports_string = ""
    for i in range(0,x_mpsoc_dim*y_mpsoc_dim):
        open_ports_string = open_ports_string + "\"" + open_ports_vector[i] + "\","
    open_ports_string = open_ports_string[0:len(open_ports_string)-1]

    #Computes the max of tasks into an app
    max_task_per_app = 0 #len(taks_list)
    for app in apps_list:
        tasks_list = app["tasks"]
        
        task_count = len( tasks_list )
       
        if task_count > max_task_per_app:
            max_task_per_app = task_count
    
   
    file_lines = []
    #---------------- VHDL SINTAX ------------------
    file_lines.append("library IEEE;\n")
    file_lines.append("use IEEE.Std_Logic_1164.all;\n")
    file_lines.append("use IEEE.std_logic_unsigned.all;\n")
    file_lines.append("use IEEE.std_logic_arith.all;\n\n")
    file_lines.append("package hemps_pkg is\n\n")
    file_lines.append("    -- paging definitions\n")
    file_lines.append("    constant PAGE_SIZE_BYTES             : integer := "+str(page_size_KB*1024)+";\n")
    file_lines.append("    constant MEMORY_SIZE_BYTES           : integer := "+str(memory_size_KB*1024)+";\n")
    #file_lines.append("    constant TOTAL_REPO_SIZE_BYTES       : integer := "+str(repo_size_bytes)+";\n")
    file_lines.append("    constant APP_NUMBER                  : integer := "+str(app_number)+";\n")
    file_lines.append("    constant MAX_TASKS_APP               : integer := "+str(max_task_per_app)+";\n")
    file_lines.append("    constant PAGE_SIZE_H_INDEX        : integer := "+str(page_size_h_index)+";\n")
    file_lines.append("    constant PAGE_NUMBER_H_INDEX      : integer := "+str(page_number_h_index)+";\n")
    file_lines.append("    -- Hemps top definitions\n")
    file_lines.append("    constant NUMBER_PROCESSORS_X      : integer := "+str(x_mpsoc_dim)+";\n")
    file_lines.append("    constant NUMBER_PROCESSORS_Y      : integer := "+str(y_mpsoc_dim)+";\n")
    file_lines.append("    constant TAM_BUFFER               : integer := "+str(noc_buffer_size)+";\n")
    file_lines.append("    constant NUMBER_PROCESSORS        : integer := "+str(x_mpsoc_dim*y_mpsoc_dim)+";\n")
    file_lines.append("    constant SIMPLE_SOC               : boolean := "+str(simple_soc)+";\n")
    file_lines.append("    constant IO_NUMBER                : integer := "+str(io_number)+";\n")
    file_lines.append("    constant LOADER_NETADDR           : std_logic_vector(31 downto 0) := x\"%x\";\n\n" % loader_addr)
    file_lines.append("    subtype kernel_str is string(1 to 3);\n")
    #file_lines.append("    type pe_type_t is array(0 to NUMBER_PROCESSORS-1) of kernel_str;\n")
    #file_lines.append("    constant pe_type : pe_type_t := ("+string_pe_type_vhdl+");\n\n")
    file_lines.append("    subtype manual_io_option is string(1 to 3);\n")
    file_lines.append("    type manual_io_type is array(0 to NUMBER_PROCESSORS-1) of manual_io_option;\n")
    file_lines.append("    constant OPEN_IO : manual_io_type := ("+open_ports_string+");\n\n")
    file_lines.append("end hemps_pkg;\n")
    
    #Use this function to create any file into testcase, it automatically only updates the old file if necessary
    writes_file_into_testcase("include/hemps_pkg.vhd", file_lines)
    
main()
