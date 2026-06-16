const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");
const globalSearch = document.querySelector("#globalSearch");

function activateView(id) {
  navItems.forEach((item) => {
    item.classList.toggle("active", item.dataset.view === id);
  });

  views.forEach((view) => {
    view.classList.toggle("active", view.id === id);
  });
}

navItems.forEach((item) => {
  item.addEventListener("click", () => activateView(item.dataset.view));
});

globalSearch.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    activateView("profile");
  }
});
