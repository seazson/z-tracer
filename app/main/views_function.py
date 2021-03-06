from flask import render_template, request, current_app, jsonify
from . import main
from .forms import FuncForm
from ..record.ftrace import Ftrace
from ..record.task import Processes

@main.route('/function', methods=['GET', 'POST'])
def function():
    return render_template('function_base.html')

@main.route('/function_callee', methods=['GET', 'POST'])
def function_callee():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    current_app.curr_device.ftrace.get_available_functions()
    form = FuncForm()
    form.depth.data = 1
    return render_template('function_callee.html', form=form)

@main.route('/function_caller', methods=['GET', 'POST'])
def function_caller():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    current_app.curr_device.ftrace.get_available_functions()
    form = FuncForm()
    form.depth.data = 1
    return render_template('function_caller.html', form=form)

@main.route('/ftrace/start', methods=['GET', 'POST'])
def ftrace_start():
    ret = 0
    func = request.form.get('func')
    depth = request.form.get('depth')
    print(func, depth)
    if func == '':
        return jsonify({'result':'需要设置函数'})
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    current_app.curr_device.ftrace.reset()
    ret = current_app.curr_device.ftrace.config_func_graph(func, depth)
    if ret == 1:
        ret = current_app.curr_device.ftrace.start()
        if ret == 'ok':
            print('start ok')
            return jsonify({'result':'ok'})
        else:
            print('start fail')
            return jsonify({'result':'运行ftrace失败，确保内核开启了ftrace'})
    else:
        return jsonify({'result':'function not support'})

@main.route('/ftrace/stop', methods=['GET', 'POST'])
def ftrace_stop():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    ret = current_app.curr_device.ftrace.stop()
    if ret == 'ok':
        current_app.curr_device.ftrace.read()
        ret = current_app.curr_device.ftrace.tostack()
        if ret > 0:
            pidhist = current_app.curr_device.ftrace.get_pid_latency_dict()
            heatmap = current_app.curr_device.ftrace.list_to_heatmap(20, 50)
            flame = current_app.curr_device.ftrace.stack_to_flamestack()
            print(pidhist, heatmap, flame)
            return jsonify({'result':'ok', 'pidhist':pidhist, 'heatmap':heatmap, 'flame':flame})
        else:
            return jsonify({'result':'no tarce data'})
    else:
        return jsonify({'result':'error'})

@main.route('/ftrace/funclist', methods=['GET', 'POST'])
def ftrace_funclist():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    current_app.curr_device.ftrace.get_available_functions()
    return jsonify({'result':'ok', 'funclist':current_app.curr_device.ftrace.available_functions})

@main.route('/ftrace/signalstart', methods=['GET', 'POST'])
def ftrace_signalstart():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    current_app.curr_device.ftrace.reset()
    ret = current_app.curr_device.ftrace.config_signal()
    if ret == 1:
        ret = current_app.curr_device.ftrace.start()
        if ret == 'ok':
            print('start ok')
            return jsonify({'result':'ok'})
        else:
            print('start fail')
            return jsonify({'result':'运行ftrace失败，确保内核开启了ftrace'})
    else:
        return jsonify({'result':'signal not support'})

@main.route('/ftrace/signalstop', methods=['GET', 'POST'])
def ftrace_signalstop():
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    ret = current_app.curr_device.ftrace.stop()
    if ret == 'ok':
        current_app.curr_device.ftrace.read()
        if not hasattr(current_app.curr_device, 'g_threads'):
            current_app.curr_device.g_threads = Processes(current_app.curr_device.zclient)
            current_app.curr_device.g_threads.scanthread()
        ret = current_app.curr_device.ftrace.signal_analyse(current_app.curr_device.g_threads.thread_dict)
        if ret:
            return jsonify({'result':'ok', 'piddict':ret})
        else:
            return jsonify({'result':'no tarce data'})
    else:
        return jsonify({'result':'error'})

@main.route('/ftrace/signalpid', methods=['GET', 'POST'])
def ftrace_signalpid():
    pid = request.form.get('pid')
    if not hasattr(current_app.curr_device, 'ftrace'):
        current_app.curr_device.ftrace = Ftrace(current_app.curr_device.zclient)
    if not hasattr(current_app.curr_device, 'g_threads'):
        current_app.curr_device.g_threads = Processes(current_app.curr_device.zclient)
    current_app.curr_device.g_threads.scanthread()
    ret = current_app.curr_device.ftrace.signal_analyse(current_app.curr_device.g_threads.thread_dict, int(pid))
    if ret:
        return jsonify({'result':'ok'})
    else:
        return jsonify({'result':'no tarce data'})
