$(document).ready(function() {
    $('a[href^="#"]').on('click', function(e) {
        const target = $(this.getAttribute('href'));
        if (target.length) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 500);
        }
    });
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    $('.animate-on-scroll').each(function() {
        $(this).css({
            opacity: '0',
            transform: 'translateY(20px)',
            transition: 'opacity 0.5s ease, transform 0.5s ease'
        });
        observer.observe(this);
    });
});