import nemo
# NeMo's ASR collection
import nemo.collections.asr as nemo_asr

# Create a Neural Factory
nf = nemo.core.NeuralModuleFactory(
    local_rank=2,
    placement = nemo.core.DeviceType.GPU,
    create_tb_writer=False)

#tb_writer = nf.tb_writer

# Path to our training manifest
train_dataset = "/scratch/nnejatis/pooya/scripts/train.json"

# Path to our validation manifest
eval_datasets = "/scratch/nnejatis/pooya/scripts/eval.json"

# QuartzNet Model definition
from ruamel.yaml import YAML

# Here we will be using separable convolutions
# with 12 blocks (k=12 repeated once r=1 from the picture above)
yaml = YAML(typ="safe")
with open("./config.yaml") as f:
    quartznet_model_definition = yaml.load(f)
labels = quartznet_model_definition['labels']
print(labels)
# Instantiate neural modules
data_layer = nemo_asr.AudioToTextDataLayer(
    manifest_filepath=train_dataset,
    labels=labels, batch_size=32)
data_layer_val = nemo_asr.AudioToTextDataLayer(
    manifest_filepath=eval_datasets,
    labels=labels, batch_size=32, shuffle=False)

data_preprocessor = nemo_asr.AudioToMelSpectrogramPreprocessor()
spec_augment = nemo_asr.SpectrogramAugmentation(rect_masks=5)

encoder = nemo_asr.JasperEncoder(
    feat_in=64,
    **quartznet_model_definition['JasperEncoder'])
decoder = nemo_asr.JasperDecoderForCTC(
    feat_in=1024, num_classes=len(labels))
ctc_loss = nemo_asr.CTCLossNM(num_classes=len(labels))
greedy_decoder = nemo_asr.GreedyCTCDecoder()

# Training DAG (Model)
audio_signal, audio_signal_len, transcript, transcript_len = data_layer()
processed_signal, processed_signal_len = data_preprocessor(
    input_signal=audio_signal, length=audio_signal_len)
aug_signal = spec_augment(input_spec=processed_signal)
encoded, encoded_len = encoder(
    audio_signal=aug_signal, length=processed_signal_len)
log_probs = decoder(encoder_output=encoded)
predictions = greedy_decoder(log_probs=log_probs)
loss = ctc_loss(
    log_probs=log_probs, targets=transcript,
    input_length=encoded_len, target_length=transcript_len)

# Validation DAG (Model)
audio_signal_v, audio_signal_len_v, transcript_v, transcript_len_v = data_layer_val()
processed_signal_v, processed_signal_len_v = data_preprocessor(
    input_signal=audio_signal_v, length=audio_signal_len_v)


encoded_v, encoded_len_v = encoder(
    audio_signal=processed_signal_v, length=processed_signal_len_v)
log_probs_v = decoder(encoder_output=encoded_v)
predictions_v = greedy_decoder(log_probs=log_probs_v)
loss_v = ctc_loss(
    log_probs=log_probs_v, targets=transcript_v,
    input_length=encoded_len_v, target_length=transcript_len_v)

from nemo.collections.asr.helpers import monitor_asr_train_progress, \
    process_evaluation_batch, process_evaluation_epoch

from functools import partial
# Callback to track loss and print predictions during training
train_callback = nemo.core.SimpleLossLoggerCallback(
    tensors=[loss, predictions, transcript, transcript_len],
    # To print logs to screen, define a print_func
    print_func=partial(
	            monitor_asr_train_progress,
        labels=labels
    ))

saver_callback = nemo.core.CheckpointCallback(
    folder="./",
    # Set how often we want to save checkpoints
    step_freq=100)

eval_callback = nemo.core.EvaluatorCallback(
    eval_tensors=[loss_v, predictions_v, transcript_v, transcript_len_v],
    # how to process evaluation batch - e.g. compute WER
    user_iter_callback=partial(
        process_evaluation_batch,
        labels=labels
        ),
    # how to aggregate statistics (e.g. WER) for the evaluation epoch
    user_epochs_done_callback=partial(
        process_evaluation_epoch, tag="DEV-CLEAN"
        ),
    eval_step=500)

nf.train(
    # Specify the loss to optimize for
    tensors_to_optimize=[loss],
    # Specify which callbacks you want to run
    callbacks=[train_callback, eval_callback, saver_callback],
    # Specify what optimizer to use
    optimizer="novograd",
    # Specify optimizer parameters such as num_epochs and lr
    optimization_params={
        "num_epochs": 50, "lr": 0.02, "weight_decay": 1e-4
        }
    )
