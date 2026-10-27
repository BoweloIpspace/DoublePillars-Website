(() => {
  if (window.lucide) window.lucide.createIcons();
  const mobileMenu = document.getElementById('mobile-menu');
  const menuButton = document.getElementById('menu-toggle');
  const navTriggers = [...document.querySelectorAll('.nav-trigger')];

  function closeMegaMenus() {
    document.querySelectorAll('.mega-menu.open').forEach((menu) => menu.classList.remove('open'));
    navTriggers.forEach((trigger) => trigger.setAttribute('aria-expanded', 'false'));
  }

  function openMegaMenu(trigger) {
    closeMegaMenus();
    const menu = document.getElementById(trigger.getAttribute('aria-controls'));
    if (!menu || window.matchMedia('(max-width: 900px)').matches) return;
    menu.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }

  navTriggers.forEach((trigger, triggerIndex) => {
    trigger.addEventListener('click', () => {
      if (trigger.getAttribute('aria-expanded') === 'true') closeMegaMenus();
      else openMegaMenu(trigger);
    });
    trigger.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openMegaMenu(trigger);
      } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        event.preventDefault();
        navTriggers[(triggerIndex + (event.key === 'ArrowRight' ? 1 : navTriggers.length - 1)) % navTriggers.length].focus();
      } else if (event.key === 'Escape') {
        closeMegaMenus();
        trigger.focus();
      }
    });
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.nav-menu-item')) closeMegaMenus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (mobileMenu?.classList.contains('open')) {
      mobileMenu.classList.remove('open');
      menuButton?.setAttribute('aria-expanded', 'false');
      menuButton?.setAttribute('aria-label', 'Open menu');
      menuButton?.focus();
      return;
    }
    const activeTrigger = document.querySelector('.nav-trigger[aria-expanded="true"]');
    if (activeTrigger) {
      closeMegaMenus();
      activeTrigger.focus();
    }
  });
  document.querySelectorAll('.mega-menu a').forEach((link) => link.addEventListener('click', closeMegaMenus));

  if (menuButton && mobileMenu) {
    menuButton.addEventListener('click', () => {
      const open = !mobileMenu.classList.contains('open');
      mobileMenu.classList.toggle('open', open);
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    mobileMenu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Open menu');
    }));
  }
})();
