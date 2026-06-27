const Header = () => {
  return (
    <header className="bg-emd-background text-emd-panel shadow-md">
      <a
        href="https://github.com/PerminovEugene/embedorium"
        target="_blank"
        className="cursor-pointer"
      >
        <div className="max-w-screen-xl mx-auto px-header-x flex justify-center items-center p-1">
          <img
            src="logo-1.png"
            alt="Embedorium logo"
            className="w-25 h-25 object-contain"
          />
          <div className="text-center">
            <h1 className="font-display tracking-widest font-bold text-emd-primary uppercase text-5xl">
              Embedorium
            </h1>
          </div>
        </div>
      </a>
    </header>
  );
};

export default Header;
