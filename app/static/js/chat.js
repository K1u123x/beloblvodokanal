$(document).ready(function() {
    var chatBox = $('#chat-box');
    var messageForm = $('#messageForm');
    var contentInput = $('#content');
    var currentUserId = $('body').data('user-id');
    
    chatBox.scrollTop(chatBox[0].scrollHeight);

    function smoothScrollToBottom() {
        chatBox.animate({ scrollTop: chatBox[0].scrollHeight }, 200);
    }

    messageForm.on('submit', function(e) {
        e.preventDefault();
        
        var message = contentInput.val().trim();
        if (message === '') return;
        
        var submitBtn = messageForm.find('button[type="submit"]');
        submitBtn.prop('disabled', true);
        
        $.ajax({
            type: 'POST',
            url: window.location.href,
            data: messageForm.serialize(),
            success: function(response) {
                contentInput.val('');
                
                $.get(window.location.href, function(html) {
                    var newChatBox = $(html).find('#chat-box');
                    if (newChatBox.length) {
                        chatBox.html(newChatBox.html());
                        smoothScrollToBottom();
                    }
                });
            },
            error: function() {
                alert('Ошибка при отправке сообщения. Попробуйте снова.');
            },
            complete: function() {
                submitBtn.prop('disabled', false);
                contentInput.focus();
            }
        });
    });

    contentInput.keypress(function(e) {
        if (e.which == 13 && !e.shiftKey) {
            e.preventDefault();
            messageForm.submit();
        }
    });

    setInterval(function() {
        var lastMsgId = $('.message-bubble:last').data('msg-id') || 0;
        $.get(window.location.href + '?last_id=' + lastMsgId, function(data) {
            if (data && data.length) {
                var hasNew = false;
                $.each(data, function(i, msg) {
                    if ($(`.message-bubble[data-msg-id="${msg.id}"]`).length === 0) {
                        var isOutgoing = msg.author_id == currentUserId;
                        var avatar = msg.author_name[0] + (msg.author_lastname ? msg.author_lastname[0] : '');
                        var msgDiv = $(`
                            <div class="message-bubble ${isOutgoing ? 'outgoing' : ''}" data-msg-id="${msg.id}" style="display: none;">
                                <div class="message-avatar">${avatar}</div>
                                <div class="message-content">
                                    <strong>${msg.author_name}</strong>
                                    <p class="mb-1">${msg.content}</p>
                                    <span class="message-time">${msg.timestamp}</span>
                                </div>
                            </div>
                        `);
                        chatBox.append(msgDiv);
                        msgDiv.fadeIn(200);
                        hasNew = true;
                    }
                });
                if (hasNew) {
                    smoothScrollToBottom();
                }
            }
        });
    }, 5000);
});