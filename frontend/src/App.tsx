import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import Layout from './components/Layout';
import Home from './pages/Home.tsx';
// Temporary comment to force TS recheck
import Dashboard from './pages/Dashboard.tsx';
import Search from './pages/Search.tsx';
import BySeller from './pages/BySeller.tsx';
import SellerTrigger from './pages/SellerTrigger.tsx';
import Recommender from './pages/Recommender.tsx';

function App() {
  return (
    <Provider store={store}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/search" element={<Search />} />
            <Route path="/by-seller" element={<BySeller />} />
            <Route path="/seller-trigger" element={<SellerTrigger />} />
            <Route path="/recommender" element={<Recommender />} />
          </Routes>
        </Layout>
      </Router>
    </Provider>
  );
}

export default App;
