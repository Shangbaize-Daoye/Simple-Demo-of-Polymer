from typing import Tuple

import wx

from apriori_prediction.region_prediction import apriori
from apriori_prediction.region_prediction import mine_and_predict_region
from positioning_data_read.file_reader import FileReader
from positioning_data_read.positioning_data_reader import PositioningDataReader
from motion_state_data_read.motion_state_data_reader import MotionStateDataReader
from motion_state_prediction.motion_state_prediction import predict_motion_state
from wifi_positioning.wifi_positioning import get_mall_wifi_db,position_it
from random import randint

association_rule_tree=None  # 存储关联规则的树形结构
motion_state_database=None  # 存储行为状态的数据库
shopping_mall=None
ref_point_db=None

app=wx.App()
win=wx.Frame(None,title="单人消费者预测模拟")
win.SetSize(575,500)

notebook=wx.Notebook(win)

bkg=wx.Panel(notebook)

st_support=wx.StaticText(bkg,label="Apriori支持度（整数）：")
st_confidence=wx.StaticText(bkg,label="Apriori置信度：50%")
btn_load_positioning_data=wx.Button(bkg,label="打开并挖掘定位记录")
btn_load_motion_data=wx.Button(bkg,label="打开行为动作记录文件")
tc_support_input=wx.TextCtrl(bkg,value="1")
slider_confidence=wx.Slider(bkg,style=wx.SL_MIN_MAX_LABELS,size=(420,0),value=50)

st_input_region_seq=wx.StaticText(bkg,label="输入模拟区域序列，区域用“-”隔开：")
tc_input_region_seq=wx.TextCtrl(bkg,value="")
btn_predict=wx.Button(bkg,label="执行预测")

st_forward_predict_num=wx.StaticText(bkg,label="指定向前预测区域的个数：")
tc_forward_predict_num=wx.TextCtrl(bkg,value="1")

result_area=wx.TextCtrl(bkg,style=wx.HSCROLL|wx.TE_MULTILINE)

#slider=wx.Slider(bkg,value=50,minValue=0,maxValue=100,style=wx.SL_AUTOTICKS|wx.SL_MIN_MAX_LABELS)
hbox1=wx.BoxSizer()
hbox1.Add(st_support,proportion=0,flag=wx.ALL,border=5)
hbox1.Add(tc_support_input,proportion=1,flag=wx.ALL,border=5)
hbox1.Add(btn_load_positioning_data,proportion=0,flag=wx.ALL,border=5)
hbox1.Add(btn_load_motion_data,proportion=0,flag=wx.ALL,border=5)
#hbox.Add(btn1,proportion=0,flag=wx.LEFT,border=0)
#hbox.Add(btn2,proportion=0,flag=wx.LEFT,border=0)
hbox2=wx.BoxSizer()
hbox2.Add(st_confidence,proportion=0,flag=wx.ALL,border=5)
hbox2.Add(slider_confidence,proportion=1,flag=wx.ALL,border=5)

hbox3=wx.BoxSizer()
hbox3.Add(wx.StaticText(bkg,label=""),proportion=0,flag=wx.ALL,border=5)

hbox4=wx.BoxSizer()
hbox4.Add(st_input_region_seq,proportion=0,flag=wx.ALL,border=5)
hbox4.Add(tc_input_region_seq,proportion=1,flag=wx.ALL,border=5)
hbox4.Add(btn_predict,proportion=0,flag=wx.ALL,border=5)

hbox5=wx.BoxSizer()
hbox5.Add(st_forward_predict_num,proportion=0,flag=wx.ALL,border=5)
hbox5.Add(tc_forward_predict_num,proportion=0,flag=wx.ALL,border=5)

hbox6=wx.BoxSizer()
hbox6.Add(result_area,proportion=1,flag=wx.ALL|wx.EXPAND,border=5)

vbox=wx.BoxSizer(wx.VERTICAL)
vbox.Add(hbox1,proportion=0,flag=wx.ALL,border=5)
vbox.Add(hbox2,proportion=0,flag=wx.ALL,border=5)
vbox.Add(hbox3,proportion=0,flag=wx.ALL,border=5)
vbox.Add(hbox4,proportion=0,flag=wx.ALL,border=5)
vbox.Add(hbox5,proportion=0,flag=wx.ALL,border=5)
vbox.Add(hbox6,proportion=1,flag=wx.ALL|wx.EXPAND,border=20)

bkg.SetSizer(vbox)

def func_on_change_slider(event):
    st_confidence.SetLabelText("Apriori置信度："+str(slider_confidence.GetValue())+"%")

def func_on_load_positioning_data(event):
    openFileDialog = wx.FileDialog(bkg,style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if openFileDialog.ShowModal() == wx.ID_CANCEL:
        return
    file_path=openFileDialog.GetPath()
    with open(file_path,"r",True) as positioning_file:
        data_set = PositioningDataReader(FileReader(positioning_file)).get_data_set()
    result_area.WriteText("成功打开定位记录文件，正在进行关联规则挖掘...\n")
    global association_rule_tree
    global motion_state_database
    association_rule_tree=apriori(data_set,int(tc_support_input.GetValue()),slider_confidence.GetValue()/100)
    if motion_state_database is None:
        result_area.WriteText("关联规则挖掘成功，已生成树形存储结构，但还没有读取行为状态数据。可以开始进行位置预测。\n")
    else:
        result_area.WriteText("关联规则挖掘成功，已生成树形存储结构，可以开始进行位置和行为状态预测。\n")


def func_on_load_ms_data_file(event):
    openFileDialog = wx.FileDialog(bkg, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if openFileDialog.ShowModal() == wx.ID_CANCEL:
        return
    file_path = openFileDialog.GetPath()
    motion_state_reader = MotionStateDataReader(file_path)
    global association_rule_tree
    global motion_state_database
    motion_state_database = motion_state_reader.database
    if association_rule_tree is None:
        result_area.WriteText("行为状态数据读取成功，已生成行为状态数据库，但关联规则还未挖掘。请打开和挖掘定位记录文件，再进行预测。\n")
    else:
        result_area.WriteText("行为状态数据读取成功，已生成行为状态数据库，可以开始进行位置和行为状态预测。\n")

def func_on_predict(event):
    global association_rule_tree
    global motion_state_database
    if association_rule_tree is None and motion_state_database is None:
        result_area.WriteText("请先打开和挖掘定位记录文件再进行位置预测。若要执行行为状态预测，请打开行为状态数据文件。\n")
        return
    elif association_rule_tree is None and motion_state_database is not None:
        result_area.WriteText("请先打开和挖掘定位记录文件再进行位置预测和行为状态预测。\n")
        return
    result: Tuple[Tuple[int], float] = mine_and_predict_region(association_rule_tree,
                                                               [int(i) for i in
                                                                tc_input_region_seq.GetValue().split("-")],
                                                               int(tc_forward_predict_num.GetValue()))
    result_area.WriteText("已经过区域序列：" + str(tc_input_region_seq.GetValue()) + "。位置预测结果：" + str(result[0]) + "。置信度：" + str(result[1]) + "。\n")
    if association_rule_tree is not None and motion_state_database is None:
        pass
    else:
        result_area.WriteText("预测的行为状态：")
        for region_id in result[0]:
            result_area.WriteText("区域id("+str(region_id)+")，行为状态("+predict_motion_state(motion_state_database,region_id)+")。")
        result_area.WriteText("\n")

slider_confidence.Bind(wx.EVT_SLIDER,func_on_change_slider)
btn_load_positioning_data.Bind(wx.EVT_BUTTON,func_on_load_positioning_data)
btn_load_motion_data.Bind(wx.EVT_BUTTON,func_on_load_ms_data_file)
btn_predict.Bind(wx.EVT_BUTTON,func_on_predict)

# WiFi定位模拟部分
wifi_bkg=wx.Panel(notebook)

st_wifi_simul_pos_num=wx.StaticText(wifi_bkg,label="模拟测准的位置数量：500    ")
slider_wifi_simul_pos_num=wx.Slider(wifi_bkg,minValue=1,maxValue=1000,style=wx.SL_MIN_MAX_LABELS,size=(500,0),value=500)
def on_wifi_slider_simul_pos_num_value_change(event):
    st_wifi_simul_pos_num.SetLabelText("模拟测准的位置数量：" + str(slider_wifi_simul_pos_num.GetValue()) + "    ")
slider_wifi_simul_pos_num.Bind(wx.EVT_SLIDER, on_wifi_slider_simul_pos_num_value_change)  # 移动滑块时同时显示数值大小

tc_wifi_output=wx.TextCtrl(wifi_bkg,style=wx.HSCROLL|wx.TE_MULTILINE|wx.TE_READONLY)

btn_wifi_choose_file=wx.Button(wifi_bkg,label="选择AP配置文件")
btn_wifi_start_simul=wx.Button(wifi_bkg,label="开始测准")
def on_btn_wifi_choose_file_click(event):
    openFileDialog = wx.FileDialog(wifi_bkg, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if openFileDialog.ShowModal() == wx.ID_CANCEL:
        return
    file_path = openFileDialog.GetPath()
    global shopping_mall
    global ref_point_db
    shopping_mall,ref_point_db=get_mall_wifi_db(file_path)
    tc_wifi_output.WriteText("已成功打开AP配置文件，可以开始测准模拟。\n")
btn_wifi_choose_file.Bind(wx.EVT_BUTTON, on_btn_wifi_choose_file_click)

def on_btn_wifi_start_simul_click(event):
    global shopping_mall
    global ref_point_db
    if shopping_mall is None and ref_point_db is None:
        tc_wifi_output.WriteText("请先打开AP配置文件，再进行测准模拟。\n")
        return
    num=slider_wifi_simul_pos_num.GetValue()
    hit_count=0
    loop_num=0
    while loop_num!=num:
        x = randint(0, 35)
        y = randint(0, 25)
        if 10<=x<=25 and 10<=y<=20:
            continue
        if x%5==0 or y%5==0:
            continue
        region_id=(y//5)*7+x//5+1
        predict_region_id=position_it((x,y),shopping_mall,ref_point_db)
        if region_id==predict_region_id:
            hit_count+=1
        loop_num+=1
    tc_wifi_output.WriteText("执行了"+str(num)+"次定位模拟，定位成功数为"+str(hit_count)+"次，定位准确率为"+str(hit_count/num)+"。\n")
btn_wifi_start_simul.Bind(wx.EVT_BUTTON, on_btn_wifi_start_simul_click)

hbox_wifi_1=wx.BoxSizer()
hbox_wifi_slider_simul_pos_num_region=wx.BoxSizer()
vbox_wifi_slider_simul_pos_num_region=wx.BoxSizer(wx.VERTICAL)
hbox_wifi_slider_simul_pos_num_region.Add(st_wifi_simul_pos_num,flag=wx.ALIGN_BOTTOM)
hbox_wifi_slider_simul_pos_num_region.Add(slider_wifi_simul_pos_num)
vbox_wifi_slider_simul_pos_num_region.Add(hbox_wifi_slider_simul_pos_num_region,flag=wx.ALIGN_CENTER)
hbox_wifi_1.Add(vbox_wifi_slider_simul_pos_num_region,proportion=1,flag=wx.ALL,border=20)

hbox_wifi_2=wx.BoxSizer()
vbox_wifi_choose_file=wx.BoxSizer(wx.VERTICAL)
vbox_wifi_start_simul=wx.BoxSizer(wx.VERTICAL)
vbox_wifi_choose_file.Add(btn_wifi_choose_file,flag=wx.ALIGN_CENTER)
vbox_wifi_start_simul.Add(btn_wifi_start_simul,flag=wx.ALIGN_CENTER)
hbox_wifi_2.Add(vbox_wifi_choose_file,proportion=1,flag=wx.ALL,border=20)
hbox_wifi_2.Add(vbox_wifi_start_simul,proportion=1,flag=wx.ALL,border=20)

hbox_wifi_3=wx.BoxSizer()
hbox_wifi_3.Add(tc_wifi_output,proportion=1,flag=wx.ALL|wx.EXPAND,border=20)

vbox_wifi=wx.BoxSizer(wx.VERTICAL)
vbox_wifi.Add(hbox_wifi_1,flag=wx.EXPAND)
vbox_wifi.Add(hbox_wifi_2,flag=wx.EXPAND)
vbox_wifi.Add(hbox_wifi_3,proportion=1,flag=wx.EXPAND)

wifi_bkg.SetSizer(vbox_wifi)

notebook.AddPage(wifi_bkg," WiFi定位测准模拟 ")
notebook.AddPage(bkg," 预测模拟 ")
win.Show()
notebook.ChangeSelection(1)
notebook.ChangeSelection(0)
app.MainLoop()
