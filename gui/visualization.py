import os
import streamlit as st
import streamlit.components.v1 as components
import tensorflow as tf
import numpy as np
import pandas as pd
import altair as alt
import visualkeras
import librosa
import io

MODEL_PATH = 'model_CNN/model.h5'
SAMPLES_TO_CONSIDER = 22050
parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "st_audiorec/frontend/build")
st_audiorec = components.declare_component("st_audiorec", path=build_dir)

mapping=[
        "right",
        "eight",
        "cat",
        "tree",
        "backward",
        "learn",
        "bed",
        "happy",
        "go",
        "dog",
        "no",
        "wow",
        "follow",
        "nine",
        "left",
        "stop",
        "three",
        "sheila",
        "one",
        "bird",
        "zero",
        "seven",
        "up",
        "visual",
        "marvin",
        "two",
        "house",
        "down",
        "six",
        "yes",
        "on",
        "five",
        "forward",
        "off",
        "four"
        ]


# @st.cache
def load_model(model_path):
    model = tf.keras.models.load_model(model_path)
    return model


def preprocess(file_path, num_mfcc=13, n_fft=2048, hop_length=512):
    """Extract MFCCs from audio file.

    :param file_path (str): Path of audio file
    :param num_mfcc (int): # of coefficients to extract
    :param n_fft (int): Interval we consider to apply STFT. Measured in # of samples
    :param hop_length (int): Sliding window for STFT. Measured in # of samples
    :return MFCCs (ndarray): 2-dim array with MFCC data of shape (# time steps, # coefficients)
    """

    # load audio file
    signal, sample_rate = librosa.load(io.BytesIO(file_path))

    if len(signal) >= SAMPLES_TO_CONSIDER:
        # ensure consistency of the length of the signal
        signal = signal[:SAMPLES_TO_CONSIDER]
    else:
        signal = np.pad(signal, (0, SAMPLES_TO_CONSIDER - signal.shape[0]))

    # extract MFCCs
    MFCCs = librosa.feature.mfcc(signal, sample_rate, n_mfcc=num_mfcc, n_fft=n_fft,
                                        hop_length=hop_length)
    return MFCCs.T




def CNN_predict(file_path):
    """
    :param file_path (str): Path to audio file to predict
    :return predicted_keyword (str): Keyword predicted by the model
    """

    # extract MFCC
    MFCCs = preprocess(file_path)

    # we need a 4-dim array to feed to the model for prediction: (# samples, # time steps, # coefficients, 1)
    MFCCs = MFCCs[np.newaxis, ..., np.newaxis]

    # get the predicted label
    predictions = model.predict(MFCCs)
    predicted_index = np.argmax(predictions)
    predicted_keyword = mapping[predicted_index]
    return (predicted_keyword, predictions.flatten())


model = load_model(MODEL_PATH)

st.markdown('# Speech command Recognition')

st.image(visualkeras.layered_view(model, legend=True), width=600)

input, output = st.columns([5, 2], gap='large')
with input:
    st.markdown('## File Input')
    uploaded_file = st.file_uploader("Upload your recording here: ", type=['wav'])
    if uploaded_file is not None:
        st.markdown('Preview')
        audio_bytes = uploaded_file.getvalue()
        st.audio(audio_bytes, format='audio/wav')
    st.markdown("## Recording Input")
    recorded_file = st_audiorec()
    

def create_visualization(file):
    predicted_keyword, confidences = CNN_predict(file)
    st.markdown(f"I heard the word \"{predicted_keyword}\"")
    # Plot
    s = 10
    ind = np.argpartition(confidences, -s)[-s:]
    kwrds = np.array(mapping)[ind]
    confs = confidences[ind]
    data = pd.DataFrame({'keyword':kwrds, 'confidence':confs})
    chart = alt.Chart(data).mark_bar().encode(
        x=alt.X('confidence', axis=alt.Axis(title='confidence')),
        y=alt.Y('keyword', sort='-x', axis=alt.Axis(title=''))
    )
    st.write(chart)

with output:
    st.markdown('## Output')
    if uploaded_file is not None:
        create_visualization(uploaded_file.getvalue())
    elif isinstance(recorded_file, dict):  # retrieve audio data
        with st.spinner('retrieving audio-recording...'):
            ind, val = zip(*recorded_file['arr'].items())
            ind = np.array(ind, dtype=int)  # convert to np array
            val = np.array(val)             # convert to np array
            sorted_ints = val[ind]
            stream = io.BytesIO(b"".join([int(v).to_bytes(1, "big") for v in sorted_ints]))
            wav_bytes = stream.read()
        create_visualization(wav_bytes)

