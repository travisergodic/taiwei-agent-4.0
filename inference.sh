# 请选手按照以下命令格式执行推理脚本

export PYTHON_ROOT=/home/aistudio/.conda/envs/paddlepaddle-env
export PATH=$PYTHON_ROOT/bin:/home/opt/cuda_tools:$PATH
export LD_LIBRARY_PATH=$PYTHON_ROOT/lib:/home/opt/nvidia_lib:$LD_LIBRARY_PATH

unset PYTHONHOME
unset PYTHONPATH

pip install qianfan redis requests

# AK和SK请自己注册获取
$PADDLEPADDLE_PYTHON_PATH tools/inference_re.py --config_file config/taiwei-agent.yaml \
                                                --dataset dataset.json \
                                                --topk 5 \
                                                --save_path result.json \
                                                --max_iter 10 8 8 7