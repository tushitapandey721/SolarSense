/* ===== SolarSense Main JS ===== */

// Smooth scroll for nav links
document.querySelectorAll('a[href^="/#"]').forEach(link => {
  link.addEventListener('click', e => {
    const target = document.querySelector(link.getAttribute('href').slice(1));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// Navbar scroll effect
const navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(0,0,0,.1)'
      : '';
  }, { passive: true });
}

// Scroll-reveal animation
const revealElements = document.querySelectorAll(
  '.step-card, .benefit-card, .testimonial-card, .stat-item'
);

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  revealElements.forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(24px)';
    el.style.transition = `opacity .5s ease ${i * 0.07}s, transform .5s ease ${i * 0.07}s`;
    observer.observe(el);
  });
}

// Contact Form
const contactForm = document.getElementById('contactForm');
if (contactForm) {
  contactForm.addEventListener('submit', async e => {
    e.preventDefault();

    const nameEl  = document.getElementById('cf-name');
    const phoneEl = document.getElementById('cf-phone');
    const cityEl  = document.getElementById('cf-city');
    const msgEl   = document.getElementById('cf-message');
    const btn     = document.getElementById('cfSubmitBtn');

    // Clear previous errors
    ['name', 'phone', 'city'].forEach(f => {
      document.getElementById(`err-${f}`).textContent = '';
    });

    document.getElementById('form-success').classList.add('hidden');
    document.getElementById('form-error').classList.add('hidden');

    const payload = {
      name: nameEl.value.trim(),
      phone: phoneEl.value.trim(),
      city: cityEl.value.trim(),
      message: msgEl.value.trim(),
    };

    btn.disabled = true;
    btn.textContent = 'Sending…';

    try {
      const res = await fetch('/api/submit-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.success) {
        document.getElementById('form-success').classList.remove('hidden');
        contactForm.reset();
      } else if (data.errors) {
        Object.entries(data.errors).forEach(([field, msg]) => {
          const errEl = document.getElementById(`err-${field}`);
          if (errEl) errEl.textContent = msg;
        });
      } else {
        document.getElementById('form-error').classList.remove('hidden');
      }
    } catch {
      document.getElementById('form-error').classList.remove('hidden');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Send Enquiry';
    }
  });
}
