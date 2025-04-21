// Sample restaurant data
const restaurants = [
    {
      name: "Sakura Sushi",
      cuisine: "Japanese",
      address: "123 Tokyo St",
    },
    {
      name: "Bella Italia",
      cuisine: "Italian",
      address: "456 Rome Ave",
    },
    {
      name: "Spice Route",
      cuisine: "Indian",
      address: "789 Delhi Blvd",
    },
    {
      name: "Tacos El Mexicano",
      cuisine: "Mexican",
      address: "321 Mexico City Rd",
    },
    {
      name: "Burger House",
      cuisine: "American",
      address: "654 NYC Lane",
    }
  ];
  
  const list = document.getElementById("restaurantList");
  
  restaurants.forEach((restaurant) => {
    const card = document.createElement("div");
    card.className = "restaurant-card";
    card.innerHTML = `
      <h3>${restaurant.name}</h3>
      <p><strong>Cuisine:</strong> ${restaurant.cuisine}</p>
      <p><strong>Address:</strong> ${restaurant.address}</p>
      <button class="view-button">View Menu</button>
    `;
    list.appendChild(card);
  });
  