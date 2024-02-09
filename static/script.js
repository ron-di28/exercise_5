let lastMessageIds = {};


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('messageForm');
    if (form) {
        form.onsubmit = async (e) => {
            e.preventDefault();
            postMessage();
        };
    }
});

async function postMessage() {
    const commentInput = document.getElementById('comment');
    const comment = commentInput.value.trim();
    const roomId = window.location.pathname.split('/')[2];

    const queryParams = new URLSearchParams({ comment: comment }).toString();
    const requestUrl = `/api/rooms/${roomId}/messages?${queryParams}`;
    console.log("Request URL:", requestUrl);

    fetch(requestUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Api-Key': WATCH_PARTY_API_KEY,
            'User-ID': WATCH_PARTY_USER_ID
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
}

document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.querySelector('.chat');
    if (chatContainer) {
        const roomID = window.location.pathname.split('/')[2];
        const messagesContainer = document.querySelector('.messages');
        while (messagesContainer.firstChild) {
            messagesContainer.removeChild(messagesContainer.firstChild);
        }
        startMessagePolling(roomID);
    }
});

function startMessagePolling(roomID) {
    setInterval(() => {
        getMessages();
    }, 100);
}

async function getMessages() {
    const roomID = window.location.pathname.split('/')[2];
    if (!lastMessageIds.hasOwnProperty(roomID)) {
        lastMessageIds[roomID] = 0;
    }
    console.log(`/api/rooms/${roomID}/messages`);

    const response = await fetch(`/api/rooms/${roomID}/messages`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Api-Key': WATCH_PARTY_API_KEY,
            'User-ID': WATCH_PARTY_USER_ID
        },
        credentials: 'include'
    });

    if (response.ok) {
        const messages = await response.json();
        messages.forEach(msg => {
            if (msg.id > lastMessageIds[roomID]) {
                createMessageElement(msg);
                lastMessageIds[roomID] = msg.id;
            }
        });
    } else {
        console.error('Failed to fetch messages');
    }
}

function createMessageElement(msg) {
    const messageElement = document.createElement('message');
    const authorElement = document.createElement('author');
    authorElement.textContent = msg.name;

    const contentElement = document.createElement('content');
    contentElement.textContent = msg.body;

    messageElement.appendChild(authorElement);
    messageElement.appendChild(contentElement);

    document.querySelector('.messages').appendChild(messageElement);
}

document.addEventListener('DOMContentLoaded', function() {
    const editIcon = document.querySelector('.display .material-symbols-outlined');
    const saveIcon = document.querySelector('.edit .material-symbols-outlined');
    const displayContainer = document.querySelector('.display');
    const editContainer = document.querySelector('.edit');
    const roomNameSpan = document.querySelector('.roomName');
    const roomNameInput = document.querySelector('.edit input');

    editIcon.addEventListener('click', function() {
        displayContainer.classList.add('hide');
        editContainer.classList.remove('hide');
        roomNameInput.value = roomNameSpan.textContent; // Pre-fill the current room name
    });

    saveIcon.addEventListener('click', function() {
        const newRoomName = roomNameInput.value.trim();
        if(newRoomName) {
            updateRoomName(newRoomName);
        }
    });
});



async function updateRoomName(newName) {
    const roomId = window.location.pathname.split('/')[2];
    try {
        const response = await fetch(`/api/rooms/${roomId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Api-Key': WATCH_PARTY_API_KEY,
                'User-ID': WATCH_PARTY_USER_ID
            },
            body: JSON.stringify({ name: newName }),
            credentials: 'include' // Include this if your endpoint requires cookies/session
        });

        if(response.ok) {
            const data = await response.json();
            // Assuming the server responds with the updated room object
            document.querySelector('.roomName').textContent = data.name;
            document.querySelector('.display').classList.remove('hide');
            document.querySelector('.edit').classList.add('hide');
        } else {
            throw new Error('Failed to update room name');
        }
    } catch(error) {
        console.error('Error updating room name:', error);
    }
}

/* For profile.html */

// TODO: Allow updating the username and password

document.addEventListener('DOMContentLoaded', function() {
    const updateUsernameBtn = document.querySelector('.username + button');
    const updatePasswordBtn = document.querySelector('.password + button');

    updateUsernameBtn.addEventListener('click', function() {
        const newUsername = document.querySelector('input.username').value;
        updateUserDetails('name', newUsername);
    });

    updatePasswordBtn.addEventListener('click', function() {
        const newPassword = document.querySelector('input.password').value;
        updateUserDetails('password', newPassword);
    });
});

function updateUserDetails(detailType, newValue) {
    let apiEndpoint = detailType === 'name' ? '/api/user/name' : '/api/user/password';
    let data = detailType === 'name' ? { newUsername: newValue } : { newPassword: newValue };
    data.userId = WATCH_PARTY_USER_ID;

    fetch(apiEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Api-Key': WATCH_PARTY_API_KEY,
            'User-ID': WATCH_PARTY_USER_ID
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
}
