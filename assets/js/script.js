'use strict';

// element toggle function
const elementToggleFunc = function (elem) { elem.classList.toggle("active"); }

// sidebar variables
const sidebar = document.querySelector("[data-sidebar]");
const sidebarBtn = document.querySelector("[data-sidebar-btn]");

// sidebar toggle functionality for mobile
sidebarBtn.addEventListener("click", function () { elementToggleFunc(sidebar); });

// testimonials variables
const overlay = document.querySelector("[data-overlay]");
const selectItems = document.querySelectorAll("[data-select-item]");
const selectValue = document.querySelector("[data-selecct-value]");
const filterBtn = document.querySelectorAll("[data-filter-btn]");

// Wait for the DOM to fully load for fade in
document.addEventListener("DOMContentLoaded", function() {
  document.body.classList.add("fade-in");
});

// add event in all select items
for (let i = 0; i < selectItems.length; i++) {
  selectItems[i].addEventListener("click", function () {
    let selectedValue = this.innerText.toLowerCase();
    selectValue.innerText = this.innerText;
    elementToggleFunc(select);
    filterFunc(selectedValue);
  });
}

// filter variables
const filterItems = document.querySelectorAll("[data-filter-item]");

const filterFunc = function (selectedValue) {
  for (let i = 0; i < filterItems.length; i++) {
    if (selectedValue === "all") {
      filterItems[i].classList.add("active");
    } else if (selectedValue === filterItems[i].dataset.category) {
      filterItems[i].classList.add("active");
    } else {
      filterItems[i].classList.remove("active");
    }
  }
}

// add event in all filter button items for large screen
let lastClickedBtn = filterBtn[0];

for (let i = 0; i < filterBtn.length; i++) {
  filterBtn[i].addEventListener("click", function () {
    let selectedValue = this.innerText.toLowerCase();
    selectValue.innerText = this.innerText;
    filterFunc(selectedValue);
    lastClickedBtn.classList.remove("active");
    this.classList.add("active");
    lastClickedBtn = this;
  });
}

// contact form variables
const form = document.querySelector("[data-form]");
const formInputs = document.querySelectorAll("[data-form-input]");
const formBtn = document.querySelector("[data-form-btn]");

// add event to all form input field
for (let i = 0; i < formInputs.length; i++) {
  formInputs[i].addEventListener("input", function () {
    // check form validation
    if (form.checkValidity()) {
      formBtn.removeAttribute("disabled");
    } else {
      formBtn.setAttribute("disabled", "");
    }
  });
}

// page navigation variables
const navigationLinks = document.querySelectorAll("[data-nav-link]");
const pages = document.querySelectorAll("[data-page]");

// add event to all nav link with fade effect
const navbar = document.querySelector(".navbar");

for (let i = 0; i < navigationLinks.length; i++) {
  navigationLinks[i].addEventListener("click", function () {
    const clickedPage = this.innerHTML.toLowerCase();
    
    // Find currently active page
    const activePage = document.querySelector("[data-page].active");
    
    // Find target page
    let targetPage = null;
    for (let j = 0; j < pages.length; j++) {
      if (clickedPage === pages[j].dataset.page) {
        targetPage = pages[j];
        break;
      }
    }
    
    // If clicking the same page, do nothing
    if (activePage === targetPage) return;
    
    // Add fade-out class to current page and entire navbar
    if (activePage) {
      activePage.classList.add("fade-out");
    }
    if (navbar) {
      navbar.classList.add("fade-out");
    }
    
    // Wait for fade-out animation, then switch pages
    setTimeout(() => {
      // Remove active and fade-out class from all pages and nav links
      for (let j = 0; j < pages.length; j++) {
        pages[j].classList.remove("active", "fade-out");
        navigationLinks[j].classList.remove("active");
      }
      
      // Remove fade-out from navbar
      if (navbar) {
        navbar.classList.remove("fade-out");
      }
      
      // Add active class to target page and nav link
      if (targetPage) {
        targetPage.classList.add("active");
        navigationLinks[i].classList.add("active");
        window.scrollTo(0, 0);
      }
    }, 250); // Match this to your CSS transition duration
  });
}