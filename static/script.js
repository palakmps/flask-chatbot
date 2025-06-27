// Chatbot Message Exchange
document.addEventListener('DOMContentLoaded', function () {
    const sendButton = document.getElementById('send-button');
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');

    // Function to send the message
    function sendMessage() {
        const inputText = userInput.value.trim();
        if (!inputText) return;

        chatWindow.innerHTML += `<div class="text-right"><strong>You:</strong> ${inputText}</div>`;
        userInput.value = '';

        // Send input to the server
        fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: inputText })
        })
        .then(response => response.json())
        .then(data => {
            const botResponse = data.response;
            chatWindow.innerHTML += `<div class="text-left"><strong>Bot:</strong> ${botResponse}</div>`;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        })
        .catch(error => console.error('Error:', error));
    }

    sendButton?.addEventListener('click', sendMessage);
    userInput?.addEventListener('keypress', function (event) {
        if (event.key === 'Enter') {
            sendMessage();
            event.preventDefault();
        }
    });
});

// Text-to-Speech Functionality
let speechInstance = null;
let voices = [];

function populateVoiceList() {
    voices = window.speechSynthesis.getVoices();
    
    if (!voices.length) {
        console.warn("No voices available yet. Retrying...");
        setTimeout(populateVoiceList, 500); // Retry after a delay
        return;
    }

    console.log("Available Voices:", voices); 
    const voiceSelect = document.getElementById('voice-select');
    if (!voiceSelect) return;

    voiceSelect.innerHTML = ''; 
    voices.forEach((voice) => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name} (${voice.lang})`;
        voiceSelect.appendChild(option);
    });
}

// Ensure voice list is populated when voices are available
window.speechSynthesis.onvoiceschanged = populateVoiceList;
setTimeout(populateVoiceList, 500); // Initial attempt with delay

document.getElementById('speak-button')?.addEventListener('click', function () {
    const textInput = document.getElementById('text-input').value;
    const selectedVoiceName = document.getElementById('voice-select').value;
    const selectedVoice = voices.find(voice => voice.name === selectedVoiceName);

    if (textInput) {
        if (speechInstance) window.speechSynthesis.cancel();

        speechInstance = new SpeechSynthesisUtterance(textInput);
        speechInstance.voice = selectedVoice || voices[0]; // Default to first available voice
        window.speechSynthesis.speak(speechInstance);
    } else {
        alert("Please enter some text to speak.");
    }
});

// Pause & Resume Buttons
document.getElementById('pause-button')?.addEventListener('click', () => window.speechSynthesis.pause());
document.getElementById('resume-button')?.addEventListener('click', () => window.speechSynthesis.resume());

// File Upload Handling
document.getElementById('read-button')?.addEventListener('click', function () {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            window.location.href = `/read?text=${encodeURIComponent(data.text)}`;
        })
        .catch(error => console.error('Error:', error));
    } else {
        alert("Please select a file to upload.");
    }
});
