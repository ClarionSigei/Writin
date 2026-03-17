// Theme toggle
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

// Check for saved theme preference
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
    body.classList.add('dark-theme');
} else if (savedTheme === 'light') {
    body.classList.remove('dark-theme');
} else {
    // Check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        body.classList.add('dark-theme');
    }
}

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-theme');
    if (body.classList.contains('dark-theme')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
});

// Mobile menu toggle
const hamburger = document.getElementById('hamburger');
const mobileNav = document.getElementById('mobileNav');

if (hamburger && mobileNav) {
    hamburger.addEventListener('click', () => {
        if (mobileNav.style.display === 'flex') {
            mobileNav.style.display = 'none';
        } else {
            mobileNav.style.display = 'flex';
        }
    });

    // Close mobile nav when a link is clicked
    const mobileLinks = document.querySelectorAll('.mobile-nav a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', () => {
            mobileNav.style.display = 'none';
        });
    });
}

// Update date/time
function updateDateTime() {
    const datetimeEl = document.getElementById('datetime');
    if (datetimeEl) {
        const now = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        datetimeEl.innerText = now.toLocaleDateString('en-US', options);
    }
}
updateDateTime();
setInterval(updateDateTime, 1000);

// File input display (for any file input with .file-custom)
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function(e) {
        const customSpan = this.closest('.file-input-wrapper')?.querySelector('.file-custom');
        if (customSpan) {
            const fileName = e.target.files[0] ? e.target.files[0].name : 'Choose file...';
            customSpan.textContent = fileName;
        }
    });
});

// Conditional fields for essay form (if present)
const instructionRadios = document.querySelectorAll('input[name="instruction_type"]');
if (instructionRadios.length) {
    const fileField = document.getElementById('file-field');
    const linkField = document.getElementById('link-field');
    const textField = document.getElementById('text-field');
    
    instructionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (fileField) fileField.style.display = 'none';
            if (linkField) linkField.style.display = 'none';
            if (textField) textField.style.display = 'none';
            
            if (this.value === 'file' && fileField) {
                fileField.style.display = 'block';
            } else if (this.value === 'link' && linkField) {
                linkField.style.display = 'block';
            } else if (this.value === 'text' && textField) {
                textField.style.display = 'block';
            }
        });
    });
}

// Conditional fields for general form (if present)
const submissionRadios = document.querySelectorAll('input[name="submission_type"]');
if (submissionRadios.length) {
    const fileSubField = document.getElementById('file-sub-field');
    const linkSubField = document.getElementById('link-sub-field');
    const textSubField = document.getElementById('text-sub-field');
    
    submissionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (fileSubField) fileSubField.style.display = 'none';
            if (linkSubField) linkSubField.style.display = 'none';
            if (textSubField) textSubField.style.display = 'none';
            
            if (this.value === 'file' && fileSubField) {
                fileSubField.style.display = 'block';
            } else if (this.value === 'link' && linkSubField) {
                linkSubField.style.display = 'block';
            } else if (this.value === 'text' && textSubField) {
                textSubField.style.display = 'block';
            }
        });
    });
}

// Price calculator for essay form (if present)
const pagesInput = document.getElementById('pages');
const deadlineSelect = document.getElementById('deadline');
const totalPriceSpan = document.getElementById('totalPrice');

function calculateTotal() {
    if (pagesInput && deadlineSelect && totalPriceSpan) {
        const pages = parseInt(pagesInput.value) || 1;
        const deadline = deadlineSelect.value;
        const rates = {'0-2': 12, '3-4': 10, '5+': 8};
        const rate = rates[deadline] || 8;
        const total = pages * rate;
        totalPriceSpan.innerText = '$' + total.toFixed(2);
    }
}

if (pagesInput && deadlineSelect && totalPriceSpan) {
    pagesInput.addEventListener('input', calculateTotal);
    deadlineSelect.addEventListener('change', calculateTotal);
    calculateTotal(); // initial
}

// Confirm deletion in admin (optional)
document.querySelectorAll('.delete-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        if (!confirm('Are you sure you want to delete this order? This action cannot be undone.')) {
            e.preventDefault();
        }
    });
});