$(document).ready(function() {
    // Загружаем настройки
    const currentTheme = localStorage.getItem('theme') || 'light';
    const accessibilityEnabled = localStorage.getItem('accessibility') === 'true';
    const fontSize = localStorage.getItem('fontSize') || 'medium';
    const accessibilityTheme = localStorage.getItem('accessibilityTheme') || 'light';
    
    // Применяем основную тему
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Функция плавного показа панели
    function showAccessibilityPanel() {
        $('#accessibilityPanel').css('display', 'block');
        setTimeout(() => $('#accessibilityPanel').css('opacity', '1'), 10);
    }
    
    function hideAccessibilityPanel() {
        $('#accessibilityPanel').css('opacity', '0');
        setTimeout(() => $('#accessibilityPanel').css('display', 'none'), 300);
    }
    
  // Применяем настройки доступности при загрузке
  if (accessibilityEnabled) {
      document.documentElement.setAttribute('data-accessibility', 'true');
      document.documentElement.setAttribute('data-font-size', fontSize);
      document.documentElement.setAttribute('data-accessibility-theme', accessibilityTheme);
      $('#toggleAccessibility').addClass('active');
      $('#normalThemeSwitcher').hide();
      $('#accessibilityPanel').css('display', 'block').css('opacity', '1');
      
      // Активируем кнопки
      $('.accessibility-font-btn').removeClass('active');
      $(`.accessibility-font-btn[data-size="${fontSize}"]`).addClass('active');
      $('.accessibility-theme-btn').removeClass('active');
      $(`.accessibility-theme-btn[data-access-theme="${accessibilityTheme}"]`).addClass('active');
  } else {
      // ВАЖНО: показываем обычные темы и скрываем панель
      $('#normalThemeSwitcher').show();
      $('#accessibilityPanel').css('display', 'none').css('opacity', '0');
      $('#toggleAccessibility').removeClass('active');
  }
    
    // Подсвечиваем активную тему
    $('.theme-btn').removeClass('active');
    $(`.theme-btn[data-theme="${currentTheme}"]`).addClass('active');
    
    // Переключение обычной темы
    $('.theme-btn').click(function() {
        const newTheme = $(this).data('theme');
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        $('.theme-btn').removeClass('active');
        $(this).addClass('active');
        
        showToast(newTheme === 'light' ? '☀️ Светлая тема' : '🌙 Тёмная тема');
    });
    
    // Переключение режима для слабовидящих
    $('#toggleAccessibility').click(function() {
        const isEnabled = document.documentElement.getAttribute('data-accessibility') === 'true';
        
        if (isEnabled) {
            // Выключаем
            document.documentElement.removeAttribute('data-accessibility');
            document.documentElement.removeAttribute('data-font-size');
            document.documentElement.removeAttribute('data-accessibility-theme');
            localStorage.setItem('accessibility', 'false');
            $(this).removeClass('active');
            $('#normalThemeSwitcher').show();
            hideAccessibilityPanel();
            showToast('Обычный режим');
        } else {
            // Включаем
            const fontSize = localStorage.getItem('fontSize') || 'medium';
            const accessibilityTheme = localStorage.getItem('accessibilityTheme') || 'light';
            
            document.documentElement.setAttribute('data-accessibility', 'true');
            document.documentElement.setAttribute('data-font-size', fontSize);
            document.documentElement.setAttribute('data-accessibility-theme', accessibilityTheme);
            localStorage.setItem('accessibility', 'true');
            
            $(this).addClass('active');
            $('#normalThemeSwitcher').hide();
            showAccessibilityPanel();
            
            // Активируем кнопки
            $('.accessibility-font-btn').removeClass('active');
            $(`.accessibility-font-btn[data-size="${fontSize}"]`).addClass('active');
            $('.accessibility-theme-btn').removeClass('active');
            $(`.accessibility-theme-btn[data-access-theme="${accessibilityTheme}"]`).addClass('active');
            
            showToast('👁️ Версия для слабовидящих');
        }
    });
    
    // Размер шрифта
    $('.accessibility-font-btn').click(function() {
        const size = $(this).data('size');
        document.documentElement.setAttribute('data-font-size', size);
        localStorage.setItem('fontSize', size);
        
        $('.accessibility-font-btn').removeClass('active');
        $(this).addClass('active');
        
        const sizeNames = { small: 'Мелкий текст', medium: 'Средний текст', large: 'Крупный текст' };
        showToast(`📏 ${sizeNames[size]}`);
    });
    
    // Тема внутри режима для слабовидящих (ИСПРАВЛЕНО)
    $('.accessibility-theme-btn').click(function() {
        const theme = $(this).data('access-theme');
        
        // Удаляем оба атрибута перед установкой нового
        document.documentElement.setAttribute('data-accessibility-theme', theme);
        localStorage.setItem('accessibilityTheme', theme);
        
        $('.accessibility-theme-btn').removeClass('active');
        $(this).addClass('active');
        
        showToast(theme === 'light' ? '☀️ Светлый фон' : '🌙 Тёмный фон');
    });
    
    function showToast(message) {
        const toast = $(`
            <div class="position-fixed bottom-0 start-50 translate-middle-x p-3" style="z-index: 9999;">
                <div class="toast show align-items-center text-white bg-primary border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>
            </div>
        `);
        $('body').append(toast);
        setTimeout(() => toast.remove(), 2000);
    }
});

function openLightbox(src, caption = 'Фото отзыва') {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImage');
    const captionEl = document.getElementById('lightboxCaption');
    
    modal.style.display = 'block';
    img.src = src;
    captionEl.textContent = caption;
    
    // Запрещаем скролл на body
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const modal = document.getElementById('lightboxModal');
    modal.style.display = 'none';
    
    // Возвращаем скролл
    document.body.style.overflow = '';
}

// Закрытие по ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLightbox();
    }
});