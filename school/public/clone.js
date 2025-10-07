// Smooth scroll
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href^="#"]');
  if (!a) return;
  const el = document.querySelector(a.getAttribute('href'));
  if (!el) return;
  e.preventDefault();
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

// Footer year
const y = document.getElementById('y');
if (y) y.textContent = new Date().getFullYear();

// Reveal on scroll
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('shown');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
document.querySelectorAll('[data-reveal]').forEach((el, i) => {
  el.style.transitionDelay = `${Math.min(i * 60, 240)}ms`;
  revealObserver.observe(el);
});

// Image reveal
const imgObserver = new IntersectionObserver((entries)=>{
  entries.forEach((entry)=>{
    if(entry.isIntersecting){
      entry.target.classList.add('shown');
      imgObserver.unobserve(entry.target);
    }
  });
},{threshold:.1});
document.querySelectorAll('img').forEach(img=>{
  img.classList.add('reveal-img');
  if(img.complete) imgObserver.observe(img); else img.addEventListener('load',()=>imgObserver.observe(img));
});

// Counters
const counters = document.querySelectorAll('.num[data-count]');
const countObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    const el = entry.target;
    const target = parseInt(el.dataset.count, 10) || 0;
    const suffix = el.dataset.suffix || '+';
    let start = 0;
    const duration = 1200;
    const startTime = performance.now();
    const step = (now) => {
      const p = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = Math.floor(start + (target - start) * eased);
      el.textContent = `${val}${suffix}`;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    countObserver.unobserve(el);
  });
}, { threshold: 0.4 });
counters.forEach((c) => countObserver.observe(c));

// Progress bar & header shadow
const progress = document.getElementById('scrollProgress');
const header = document.querySelector('.site-header');
const onScroll = () => {
  const sTop = window.scrollY;
  const docH = document.body.scrollHeight - window.innerHeight;
  const p = docH > 0 ? (sTop / docH) * 100 : 0;
  if (progress) progress.style.width = `${p}%`;
  if (header) header.classList.toggle('scrolled', sTop > 8);
};
document.addEventListener('scroll', onScroll, { passive:true });
window.addEventListener('load', onScroll);

// Back to top
const toTop = document.getElementById('toTop');
const toggleTop = () => toTop?.classList.toggle('show', window.scrollY > 400);
document.addEventListener('scroll', toggleTop, { passive:true });
window.addEventListener('load', toggleTop);
toTop?.addEventListener('click', () => window.scrollTo({ top:0, behavior:'smooth' }));

// Floating particles in hero
const canvas = document.getElementById('bgParticles');
if (canvas) {
  const ctx = canvas.getContext('2d');
  const DPR = window.devicePixelRatio || 1;
  let w, h, particles;
  
  function resize() {
    w = canvas.clientWidth; 
    h = canvas.clientHeight;
    canvas.width = w * DPR; 
    canvas.height = h * DPR; 
    ctx.scale(DPR, DPR);
    particles = new Array(25).fill(0).map(() => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: 1 + Math.random() * 2,
      vx: -0.2 + Math.random() * 0.4,
      vy: -0.2 + Math.random() * 0.4,
      c: ['#60a5fa', '#22d3ee', '#f59e0b'][Math.floor(Math.random() * 3)]
    }));
  }
  
  function step() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach((p, i) => {
      p.x += p.vx; 
      p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1; 
      if (p.y < 0 || p.y > h) p.vy *= -1;
      
      // Pulse
      const pulse = Math.sin(Date.now() * 0.001 + i) * 0.3 + 0.7;
      const size = p.r * pulse;
      
      ctx.beginPath(); 
      ctx.arc(p.x, p.y, size, 0, Math.PI * 2); 
      ctx.fillStyle = p.c; 
      ctx.globalAlpha = 0.4 * pulse; 
      ctx.fill(); 
      ctx.globalAlpha = 1;
    });
    requestAnimationFrame(step);
  }
  
  resize(); 
  step();
  window.addEventListener('resize', resize);

  // Orbiting dots animation
  const orbiters = document.querySelectorAll('.orbiter');
  function animateOrbiters(time){
    orbiters.forEach((o, i)=>{
      const speed = parseFloat(o.dataset.speed || '12');
      const radius = parseFloat(o.dataset.radius || '120');
      const angle = (time/1000) * (60/speed) + i;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      o.style.transform = `translate(calc(50% + ${x}px), calc(50% + ${y}px)) translate(-50%, -50%)`;
    });
    requestAnimationFrame(animateOrbiters);
  }
  requestAnimationFrame(animateOrbiters);

  // Interactive cursor follower and enhanced parallax
  const art = document.querySelector('.hero-art');
  const cursorFollower = document.querySelector('.cursor-follower');
  
  art?.addEventListener('mousemove', (e)=>{
    const r = art.getBoundingClientRect();
    const x = (e.clientX - (r.left + r.width/2)) / r.width;
    const y = (e.clientY - (r.top + r.height/2)) / r.height;
    
    const orbit = document.querySelector('.orbit');
    if (orbit) orbit.style.transform = `translateY(${Math.sin(Date.now()/1000)*3}px) rotateX(${y*8}deg) rotateY(${x*-8}deg)`;
    
    if (cursorFollower) {
      cursorFollower.style.left = `${e.clientX - r.left - 10}px`;
      cursorFollower.style.top = `${e.clientY - r.top - 10}px`;
      cursorFollower.style.opacity = '0.8';
    }
    
    const shapes = document.querySelectorAll('.shape');
    shapes.forEach((shape, i) => {
      const intensity = 0.1 + (i * 0.05);
      shape.style.transform = `translate(${x * 20 * intensity}px, ${y * 20 * intensity}px)`;
    });
  });
  
  art?.addEventListener('mouseleave', ()=>{
    const orbit = document.querySelector('.orbit');
    if (orbit) orbit.style.transform = '';
    if (cursorFollower) cursorFollower.style.opacity = '0';
    const shapes = document.querySelectorAll('.shape');
    shapes.forEach(shape => { shape.style.transform = ''; });
  });
}

// Card tilt effect
function addTilt(selector) {
  document.querySelectorAll(selector).forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      const rx = (y - 0.5) * 8;
      const ry = (x - 0.5) * -8;
      card.style.transform = `perspective(600px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
    });
    card.addEventListener('mouseleave', () => { card.style.transform = ''; });
  });
}
addTilt('.card');
addTilt('.feature');

// Active nav link on scroll
const navLinks = [...document.querySelectorAll('.nav a')].filter(a=>!a.classList.contains('btn'));
const sections = ['#programs','#facilities','#contact'].map(id => document.querySelector(id)).filter(Boolean);
const setActive = () => {
  const yPos = window.scrollY + 120;
  let current = sections[0];
  sections.forEach(sec => { if (sec.offsetTop <= yPos) current = sec; });
  navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${current.id}`));
};
document.addEventListener('scroll', setActive, { passive:true });
window.addEventListener('load', setActive);

// Newsletter toast
const newsletter = document.querySelector('.newsletter');
newsletter?.addEventListener('submit', (e) => {
  e.preventDefault();
  const email = document.getElementById('newsletterEmail');
  if (!email?.value) return;
  const toast = document.createElement('div');
  toast.textContent = 'Thanks for subscribing!';
  toast.style.position = 'fixed';
  toast.style.bottom = '24px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.background = '#2563eb';
  toast.style.color = '#fff';
  toast.style.padding = '10px 14px';
  toast.style.borderRadius = '10px';
  toast.style.boxShadow = '0 12px 24px rgba(37,99,235,.35)';
  document.body.appendChild(toast);
  setTimeout(()=>toast.remove(), 2000);
  e.target.reset();
});

// Admissions modal logic
(function(){
  console.log('Initializing admissions modal...');
  
  const modal = document.getElementById('admissionsModal');
  if(!modal) {
    console.error('Admissions modal not found!');
    return;
  }
  console.log('Admissions modal found:', modal);
  
  // Step elements
  const steps = {
    overview: document.getElementById('stepOverview'),
    details: document.getElementById('stepDetails'),
    documents: document.getElementById('stepDocuments'),
    fees: document.getElementById('stepFees'),
    payment: document.getElementById('stepPayment'),
    onlinePayment: document.getElementById('stepOnlinePayment'),
    confirmation: document.getElementById('stepConfirmation')
  };
  
  // Buttons
  const openHeader = document.getElementById('openAdmissionsHeader');
  const openCard = document.getElementById('openAdmissionsCard');
  const closeBtn = document.getElementById('closeAdmissions');
  
  console.log('Button elements:', { openHeader, openCard, closeBtn });
  const backdrop = modal.querySelector('[data-close-modal]');
  const startProcess = document.getElementById('startAdmissionProcess');
  const studentForm = document.getElementById('studentDetailsForm');
  const admissionCode = document.getElementById('admissionCode');
  const codeTitle = document.getElementById('codeTitle');
  const codeNote = document.getElementById('codeNote');
  const nextStepsList = document.getElementById('nextStepsList');
  
  // Navigation buttons
  const backToOverview = document.getElementById('backToOverview');
  const nextToFees = document.getElementById('nextToFees');
  const backToDetails = document.getElementById('backToDetails');
  const nextToPayment = document.getElementById('nextToPayment');
  const backToFees = document.getElementById('backToFees');
  const proceedPayment = document.getElementById('proceedPayment');
  const backToPayment = document.getElementById('backToPayment');
  const confirmOnlinePayment = document.getElementById('confirmOnlinePayment');
  const finishProcess = document.getElementById('finishProcess');
  
  let currentStep = 'overview';
  let formData = {};
  let submittedToBackend = false;

  async function submitApplication() {
    if (submittedToBackend) return; // avoid duplicate submissions
    try {
      const selectedMethodEl = document.querySelector('input[name="paymentMethod"]:checked');
      const selectedMethod = selectedMethodEl ? selectedMethodEl.value : '';
      const status = selectedMethod === 'online' ? 'confirmed' : 'pending';
      const payload = {
        studentName: formData.studentName || '',
        class: formData.class || '',
        section: formData.section || '',
        fatherPhone: formData.fatherPhone || '',
        email: formData.email || '',
        address: formData.address || '',
        status
      };
      const res = await fetch('/admissions/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const out = await res.json().catch(() => ({ success: false }));
      if (res.ok && out.success) {
        submittedToBackend = true;
        console.log('Admission saved with id:', out.admission_id);
        localStorage.setItem('admission_id', String(out.admission_id));
        showToast('Application submitted to school. Ref ID: ' + out.admission_id, 'success');
      } else {
        console.warn('Failed to save application:', out);
        showToast('Could not save application online. Please contact school.', 'error');
      }
    } catch (err) {
      console.error('Error submitting application', err);
      showToast('Network error while saving application.', 'error');
    }
  }

  function open(){ 
    console.log('Opening admissions modal...');
    modal.classList.add('show'); 
    document.body.style.overflow='hidden'; 
    document.body.classList.add('admissions-open');
    showStep('overview');
    console.log('Modal opened successfully');
  }
  
  function close(){ 
    modal.classList.remove('show'); 
    document.body.style.overflow=''; 
    document.body.classList.remove('admissions-open');
    showStep('overview');
    formData = {};
  }
  
  function showStep(stepName) {
    Object.values(steps).forEach(step => step.style.display = 'none');
    if(steps[stepName]) {
      steps[stepName].style.display = 'block';
      currentStep = stepName;
    }
  }
  
  function generateAdmissionCode(name, dob) {
    const nameCode = name.replace(/\s+/g, '').substring(0, 2).toUpperCase();
    const dobCode = dob.replace(/-/g, '').substring(2, 4);
    const randomCode = Math.random().toString(36).substring(2, 4).toUpperCase();
    return `TES${nameCode}${dobCode}${randomCode}`;
  }
  
  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.background = type === 'success' ? '#16a34a' : '#dc2626';
    toast.style.color = '#fff';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '10px';
    toast.style.boxShadow = '0 12px 24px rgba(0,0,0,.2)';
    toast.style.zIndex = '1000';
    toast.style.fontWeight = '600';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  // Event listeners
  openHeader && openHeader.addEventListener('click', (e) => { e.preventDefault(); console.log('Header admissions clicked'); open(); });
  openCard && openCard.addEventListener('click', (e) => { e.preventDefault(); console.log('Apply Now button clicked'); open(); });
  closeBtn && closeBtn.addEventListener('click', close);
  backdrop && backdrop.addEventListener('click', close);
  document.addEventListener('keydown', (e) => { 
    if(e.key === 'Escape' && modal.classList.contains('show')) close(); 
  });

  // Step navigation
  startProcess && startProcess.addEventListener('click', () => showStep('details'));
  backToOverview && backToOverview.addEventListener('click', () => showStep('overview'));
  nextToFees && nextToFees.addEventListener('click', () => showStep('fees'));
  backToDetails && backToDetails.addEventListener('click', () => showStep('details'));
  nextToPayment && nextToPayment.addEventListener('click', () => showStep('payment'));
  backToFees && backToFees.addEventListener('click', () => showStep('fees'));
  proceedPayment && proceedPayment.addEventListener('click', () => {
    const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked');
    if (!paymentMethod) {
      showToast('Please select a payment method.', 'error');
      return;
    }
    
    if (paymentMethod.value === 'online') {
      showStep('onlinePayment');
    } else if (paymentMethod.value === 'offline') {
      // For offline payment, go directly to confirmation without code generation
      showStep('confirmation');
      submitApplication();
    }
  });

  backToPayment && backToPayment.addEventListener('click', () => showStep('payment'));
  
  confirmOnlinePayment && confirmOnlinePayment.addEventListener('click', () => {
    showToast('Payment confirmed! Generating admission code...', 'success');
    setTimeout(() => {
      showStep('confirmation');
      submitApplication();
    }, 1500);
  });
  finishProcess && finishProcess.addEventListener('click', async () => {
    if (!submittedToBackend) {
      await submitApplication();
    }
    showToast('Application submitted successfully! We will contact you soon.', 'success');
    close();
  });

  // Form submission
  studentForm && studentForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(studentForm);
    const required = ['studentName', 'dob', 'class', 'gender', 'fatherName', 'motherName', 'fatherPhone', 'email', 'address'];
    
    for(const key of required) {
      if(!(fd.get(key) || '').toString().trim()) {
        showToast('Please fill all required fields.', 'error');
        return;
      }
    }
    
    // Store form data
    formData = Object.fromEntries(fd.entries());
    showStep('documents');
  });

  // Document upload handlers
  const fileInputs = modal.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const label = e.target.nextElementSibling;
      if(e.target.files.length > 0) {
        label.textContent = `${e.target.files.length} file(s) selected`;
        label.style.background = '#10b981';
        label.style.color = '#fff';
      } else {
        label.textContent = 'Upload';
        label.style.background = '';
        label.style.color = '';
      }
    });
  });

  // Generate admission code when reaching confirmation step (only for online payments)
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if(mutation.type === 'attributes' && mutation.attributeName === 'style') {
        if(steps.confirmation.style.display === 'block' && formData.studentName && formData.dob) {
          const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked');
          
          if (paymentMethod && paymentMethod.value === 'online') {
            // Generate code only for online payments
            const code = generateAdmissionCode(formData.studentName, formData.dob);
            if(admissionCode) {
              admissionCode.textContent = code;
              admissionCode.style.color = '#1d4ed8';
              // Store code in localStorage for future reference
              localStorage.setItem('admissionCode', code);
              localStorage.setItem('admissionData', JSON.stringify(formData));
            }
            if(codeTitle) codeTitle.textContent = 'Your Admission Code';
            if(codeNote) codeNote.textContent = 'Save this code for future reference. You\'ll need it for admission confirmation.';
            if(nextStepsList) {
              nextStepsList.innerHTML = `
                <li>Our team will review your application within 2-3 business days</li>
                <li>You'll receive a call for document verification</li>
                <li>An interaction session will be scheduled</li>
                <li>Final admission confirmation will be provided</li>
              `;
            }
          } else {
            // For offline payments, show different message
            if(admissionCode) {
              admissionCode.textContent = 'OFFLINE-PENDING';
              admissionCode.style.color = '#f59e0b';
            }
            if(codeTitle) codeTitle.textContent = 'Payment Status';
            if(codeNote) codeNote.textContent = 'Please visit the school office to complete payment and receive your admission code.';
            if(nextStepsList) {
              nextStepsList.innerHTML = `
                <li>Visit school office with required documents</li>
                <li>Complete payment (Cash/Cheque)</li>
                <li>Receive your admission code</li>
                <li>Document verification will be done on-site</li>
                <li>Final admission confirmation will be provided</li>
              `;
            }
          }
        }
      }
    });
  });

  observer.observe(steps.confirmation, { attributes: true, attributeFilter: ['style'] });
})();

// Global function to open admissions modal
function openAdmissionsModal() {
  const modal = document.getElementById('admissionsModal');
  if (modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    document.body.classList.add('admissions-open');
    
    // Reset to first step
    const overviewStep = document.getElementById('stepOverview');
    if (overviewStep) {
      overviewStep.style.display = 'block';
    }
    
    // Hide other steps
    const allSteps = document.querySelectorAll('.admissions-step');
    allSteps.forEach(step => {
      if (step.id !== 'stepOverview') {
        step.style.display = 'none';
      }
    });
  }
}

// Simple backup click handler for Apply Now button
document.addEventListener('DOMContentLoaded', function() {
  const applyNowBtn = document.getElementById('openAdmissionsCard');
  if (applyNowBtn) {
    console.log('Apply Now button found, adding backup handler');
    applyNowBtn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log('Apply Now button clicked (backup handler)');
      
      const modal = document.getElementById('admissionsModal');
      if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        document.body.classList.add('admissions-open');
        console.log('Modal opened via backup handler');
      } else {
        console.error('Modal not found in backup handler');
      }
    });
  } else {
    console.error('Apply Now button not found');
  }
  
  // Test modal and button existence
  setTimeout(() => {
    const testBtn = document.getElementById('openAdmissionsCard');
    const modal = document.getElementById('admissionsModal');
    
    if (testBtn) {
      console.log('✅ Apply Now button is properly connected');
      console.log('Button element:', testBtn);
    } else {
      console.error('❌ Apply Now button not found after DOM load');
    }
    
    if (modal) {
      console.log('✅ Admissions modal found');
      console.log('Modal element:', modal);
    } else {
      console.error('❌ Admissions modal not found');
    }
  }, 1000);
});

// Contact Modal Logic
(function(){
  const contactModal = document.getElementById('contactModal');
  if(!contactModal) return;
  
  // Buttons
  const openContactBtn = document.getElementById('openContactModal');
  const openContactFooterBtn = document.getElementById('openContactModalFooter');
  const closeContactBtn = document.getElementById('closeContactModal');
  const closeContactFormBtn = document.getElementById('closeContactForm');
  const contactBackdrop = contactModal.querySelector('[data-close-contact-modal]');
  const contactForm = document.getElementById('contactForm');
  
  function openContactModal() {
    contactModal.classList.add('show');
    document.body.style.overflow = 'hidden';
    document.body.classList.add('contact-open');
  }
  
  function closeContactModal() {
    contactModal.classList.remove('show');
    document.body.style.overflow = '';
    document.body.classList.remove('contact-open');
    if(contactForm) contactForm.reset();
  }
  
  // Event listeners
  openContactBtn && openContactBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openContactModal();
  });
  
  openContactFooterBtn && openContactFooterBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openContactModal();
  });
  
  closeContactBtn && closeContactBtn.addEventListener('click', closeContactModal);
  closeContactFormBtn && closeContactFormBtn.addEventListener('click', closeContactModal);
  contactBackdrop && contactBackdrop.addEventListener('click', closeContactModal);
  
  document.addEventListener('keydown', (e) => {
    if(e.key === 'Escape' && contactModal.classList.contains('show')) {
      closeContactModal();
    }
  });
  
  // Form submission
  contactForm && contactForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(contactForm);
    const data = Object.fromEntries(formData.entries());
    
    // Show success message
    const toast = document.createElement('div');
    toast.textContent = 'Message sent successfully! We\'ll get back to you soon.';
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.background = '#16a34a';
    toast.style.color = '#fff';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '10px';
    toast.style.boxShadow = '0 12px 24px rgba(0,0,0,.2)';
    toast.style.zIndex = '1000';
    toast.style.fontWeight = '600';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
    
    // Reset form and close modal
    contactForm.reset();
    closeContactModal();
  });
})();

// Student Portal Link Handler
document.addEventListener('DOMContentLoaded', function() {
  console.log('Looking for student portal link...');
  
  const studentPortalLink = document.querySelector('a[href="student-portal.html"]');
  console.log('Student portal link found:', studentPortalLink);
  
  if (studentPortalLink) {
    console.log('Adding click event listener to student portal link');
    
    // Add visual feedback that the button is clickable
    studentPortalLink.style.cursor = 'pointer';
    studentPortalLink.style.position = 'relative';
    studentPortalLink.style.zIndex = '999';
    
    studentPortalLink.addEventListener('click', function(e) {
      console.log('Student portal link clicked!');
      e.preventDefault();
      
      // Show loading message
      const toast = document.createElement('div');
      toast.textContent = 'Opening Student Portal...';
      toast.style.position = 'fixed';
      toast.style.bottom = '24px';
      toast.style.left = '50%';
      toast.style.transform = 'translateX(-50%)';
      toast.style.background = '#3b82f6';
      toast.style.color = '#fff';
      toast.style.padding = '12px 20px';
      toast.style.borderRadius = '10px';
      toast.style.boxShadow = '0 12px 24px rgba(0,0,0,.2)';
      toast.style.zIndex = '1000';
      toast.style.fontWeight = '600';
      document.body.appendChild(toast);
      
      // Open the portal after a short delay
      setTimeout(() => {
        window.open('student-portal.html', '_blank');
        toast.remove();
      }, 500);
    });
    
    // Also add mouse enter event for debugging
    studentPortalLink.addEventListener('mouseenter', function() {
      console.log('Mouse entered student portal link');
    });
    
  } else {
    console.error('Student portal link not found!');
    
    // Try alternative selectors
    const altLink = document.querySelector('a[href*="student-portal"]');
    console.log('Alternative link found:', altLink);
    
    const allLinks = document.querySelectorAll('a');
    console.log('All links on page:', allLinks);
  }
});

// Global function for onclick
function openStudentPortal() {
  console.log('openStudentPortal function called');
  
  // Show loading message
  const toast = document.createElement('div');
  toast.textContent = 'Opening Student Portal...';
  toast.style.position = 'fixed';
  toast.style.bottom = '24px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.background = '#3b82f6';
  toast.style.color = '#fff';
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '10px';
  toast.style.boxShadow = '0 12px 24px rgba(0,0,0,.2)';
  toast.style.zIndex = '1000';
  toast.style.fontWeight = '600';
  document.body.appendChild(toast);
  
  // Open the portal after a short delay
  setTimeout(() => {
    window.open('student-portal.html', '_blank');
    toast.remove();
  }, 500);
}



  
