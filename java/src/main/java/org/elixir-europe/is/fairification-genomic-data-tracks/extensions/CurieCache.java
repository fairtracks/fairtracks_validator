package org.elixir_europe.is.fairification_genomic_data_tracks.extensions;

import java.io.File;
import java.io.IOException;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import java.util.function.BiConsumer;
import java.util.function.BiFunction;
import java.util.function.Consumer;
import java.util.function.Function;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.sqlite.SQLiteConfig;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

import org.xml.sax.SAXException;

public class CurieCache
	implements Map<String, Curie>, AutoCloseable
{
	// Constants
	private final static String CURIE_MIRIAM_LINK="https://www.ebi.ac.uk/miriam/main/export/xml/";
	private final static String MIRIAM_NS="http://www.biomodels.net/MIRIAM/";
	
	// Metadata table
	private final static String METADATA_DDL =
	"CREATE TABLE metadata (\n" +
	"last_generated DATETIME NOT NULL,\n" +
	"last_updated DATETIME NOT NULL\n" +
	")";
	
	// Prefixes table
	private final static String NAMESPACES_DDL =
	"CREATE TABLE namespaces (\n" +
	"id VARCHAR(32) NOT NULL,\n" +
	"namespace VARCHAR(64) NOT NULL,\n" +
	"name VARCHAR(64) NOT NULL,\n" +
	"pattern VARCHAR(4096) NOT NULL,\n" +
	"PRIMARY KEY (id)\n" +
	")";
	
	// Index on the namespace
	private final static String NAMESPACES_IDX_DDL =
	"CREATE INDEX namespaces_namespace ON namespaces(namespace)";
	
	// Update check query
	private final static String UPDATE_CHECK_DML =
	"SELECT DATETIME('NOW','-7 DAYS') > last_generated\n" +
	"FROM metadata";
	
	// Update check with date query
	private final static String UPDATE_CHECK_DATE_DML =
	"SELECT TRUE\n" +
	"FROM metadata\n" +
	"WHERE DATETIME(last_updated) >= ?";
	
	// Update last generated metadata
	private final static String UPDATE_GENERATED_DML =
	"UPDATE metadata SET last_generated = ?";
	
	// Delete the contents of the namespaces table
	private final static String NAMESPACES_DELETE_DML =
	"DELETE FROM namespaces";
	
	// Delete the contents of the metadata table
	private final static String METADATA_DELETE_DML =
	"DELETE FROM metadata";
	
	// Insert the contents into the metadata table
	private final static String METADATA_INSERT_DML =
	"INSERT INTO metadata VALUES (?,?)";
	
	// Insert the contents into the namespaces table
	private final static String NAMESPACES_INSERT_DML =
	"INSERT INTO namespaces(id,namespace,pattern,name) VALUES (?,?,?,?)";
	
	// Count the number of namespaces
	private final static String NAMESPACES_COUNT_DML =
	"SELECT COUNT(*) FROM namespaces";
	
	// Iterate over the available namespace entries
	private final static String NAMESPACES_ENTRIES_DML =
	"SELECT id,namespace,name,pattern FROM namespaces";
	
	// Get a Curie entry which matches either the namespace or the id
	private final static String NAMESPACES_GET_DML =
	"SELECT id,namespace,name,pattern\n" +
	"FROM namespaces\n" +
	"WHERE\n" +
	"namespace = ?\n" +
	"OR\n" +
	"id = ?";
	
	// Does it contain an entry which matches either the namespace or the id?
	private final static String NAMESPACES_HAS_DML =
	"SELECT TRUE\n" +
	"FROM namespaces\n" +
	"WHERE\n" +
	"namespace = ?\n" +
	"OR\n" +
	"id = ?";
	
	// Does it contain an entry which matches either the namespace or the id?
	private final static String NAMESPACES_HAS_VALUE_DML =
	"SELECT TRUE\n" +
	"FROM namespaces\n" +
	"WHERE\n" +
	"id = ?\n" +
	"AND\n" +
	"namespace = ?\n" +
	"AND\n" +
	"name = ?\n" +
	"AND\n" +
	"pattern = ?";
	
	// Instance properties
	private Connection conn;
	protected File dbfile;
	
	// Constructors
	public CurieCache()
		throws SQLException, ParserConfigurationException, SAXException, IOException
	{
		this("curie_cache.sqlite");
	}
	
	public CurieCache(String filename)
		throws SQLException, ParserConfigurationException, SAXException, IOException
	{
		this(new File(filename));
	}
	
	public CurieCache(File file)
		throws SQLException, ParserConfigurationException, SAXException, IOException
	{
		dbfile = file;
		boolean existsCache = file.exists() && file.isFile() && file.length() > 0;
		boolean initializeCache = ! existsCache;
		
		// Opening / creating the database, with normal locking
		// and date parsing
		
		// db parameters
		String jdbcUrl = "jdbc:sqlite:"+file.getAbsolutePath();
		SQLiteConfig cfg = new SQLiteConfig();
		//cfg.enforceForeignKeys(true);
		cfg.setLockingMode(SQLiteConfig.LockingMode.NORMAL);
		cfg.setJournalMode(SQLiteConfig.JournalMode.WAL);
		
		// create a connection to the database
		conn = DriverManager.getConnection(jdbcUrl, cfg.toProperties());
		
		conn.setAutoCommit(false);
		
		// Database structures
		try(Statement stm = conn.createStatement()) {
			boolean updateDatabase = initializeCache;
			
			if(initializeCache) {
				// Metadata table
				stm.executeUpdate(METADATA_DDL);
				
				// Prefixes table
				stm.executeUpdate(NAMESPACES_DDL);
				
				// Index on the namespace
				stm.executeUpdate(NAMESPACES_IDX_DDL);
			} else {
				// Should we download
				stm.executeQuery(UPDATE_CHECK_DML);
				try(ResultSet rs = stm.executeQuery(UPDATE_CHECK_DML)) {
					if(rs.next()) {
						updateDatabase = true;
					}
				}
			}
			
			if(updateDatabase) {
				// Download the registry to parse it
				DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
				dbf.setNamespaceAware(true);
				DocumentBuilder domB = dbf.newDocumentBuilder();
				Document curie_dom = domB.parse(CURIE_MIRIAM_LINK);
				
				Element root = curie_dom.getDocumentElement();
				// Does the document have the update dates?
				if(root.hasAttribute("date") && root.hasAttribute("data-version")) {
					ZonedDateTime last_generated = ZonedDateTime.parse(root.getAttribute("date"), DateTimeFormatter.RFC_1123_DATE_TIME);
					ZonedDateTime last_updated = ZonedDateTime.parse(root.getAttribute("data-version"), DateTimeFormatter.RFC_1123_DATE_TIME);
					String last_generated_str = DateTimeFormatter.ISO_OFFSET_DATE_TIME.format(last_generated);
					String last_updated_str = DateTimeFormatter.ISO_OFFSET_DATE_TIME.format(last_updated);
					
					boolean updated = false;
					try(PreparedStatement psuc = conn.prepareStatement(UPDATE_CHECK_DATE_DML)) {
						psuc.setString(1,last_updated_str);
						
						try(ResultSet rs = psuc.executeQuery()) {
							updated = rs.next();
						}
					}
					
					if(updated) {
						try(PreparedStatement psu = conn.prepareStatement(UPDATE_GENERATED_DML)) {
							psu.setString(1,last_generated_str);
							psu.executeUpdate();
						}
					} else {
						// It is time to drop everything and start again
						stm.execute(NAMESPACES_DELETE_DML);
						stm.execute(METADATA_DELETE_DML);
						
						try(PreparedStatement psm = conn.prepareStatement(METADATA_INSERT_DML)) {
							psm.setString(1,last_generated_str);
							psm.setString(2,last_updated_str);
							
							psm.executeUpdate();
						}
						
						try(PreparedStatement psn = conn.prepareStatement(NAMESPACES_INSERT_DML)) {
							for(Node node = root.getFirstChild(); node != null; node = node.getNextSibling()) {
								if(node.getNodeType()==Node.ELEMENT_NODE && "datatype".equals(node.getLocalName()) && MIRIAM_NS.equals(node.getNamespaceURI())) {
									Element elem = (Element)node;
									
									psn.setString(1,elem.getAttribute("id"));
									psn.setString(2,elem.getElementsByTagNameNS(MIRIAM_NS,"namespace").item(0).getFirstChild().getNodeValue());
									psn.setString(3,elem.getAttribute("pattern"));
									psn.setString(4,elem.getElementsByTagNameNS(MIRIAM_NS,"name").item(0).getFirstChild().getNodeValue());
									
									psn.executeUpdate();
								}
							}
						}
					}
				}
			}
			
			conn.commit();
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			throw outer;
		}
	}
	
	@Override
	public void close()
		throws SQLException
	{
		conn.close();
	}
	
	@Override
	protected void finalize()
		throws Throwable
	{
		close();
	}
	
	public void clear() {
		throw new UnsupportedOperationException("Read only Curie cache");
		
		/*
		try(Statement stm = conn.createStatement()) {
			stm.execute(NAMESPACES_DELETE_DML);
			stm.execute(METADATA_DELETE_DML);
			
			conn.commit();
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			throw outer;
		}
		*/
	}
	
	public boolean containsKey(Object key) {
		if(key instanceof String) {
			try(PreparedStatement pstm = conn.prepareStatement(NAMESPACES_HAS_DML)) {
				String keyS = (String)key;
				pstm.setString(1,keyS);
				pstm.setString(2,keyS);
				
				try(ResultSet rs = pstm.executeQuery()) {
					return rs.next();
				}
			} catch(SQLException outer) {
				try {
					conn.rollback();
				} catch(SQLException inner) {
					outer.setNextException(inner);
				}
				
				// We cannot throw it because the interface does not allow it
				// throw outer;
			}
		} else {
			throw new ClassCastException();
		}
		
		return false;
	}
	
	public boolean containsValue(Object value) {
		if(value instanceof Curie) {
			try(PreparedStatement pstm = conn.prepareStatement(NAMESPACES_HAS_VALUE_DML)) {
				Curie valueC = (Curie)value;
				pstm.setString(1,valueC.id);
				pstm.setString(2,valueC.namespace);
				pstm.setString(3,valueC.name);
				pstm.setString(4,valueC.pattern);
				
				try(ResultSet rs = pstm.executeQuery()) {
					return rs.next();
				}
			} catch(SQLException outer) {
				try {
					conn.rollback();
				} catch(SQLException inner) {
					outer.setNextException(inner);
				}
				
				// We cannot throw it because the interface does not allow it
				// throw outer;
			}
		} else {
			throw new ClassCastException();
		}
		
		return false;
	}
	
	public Set<Map.Entry<String,Curie>> entrySet() {
		HashMap<String,Curie> retval = new HashMap<>();
		
		try(Statement stm = conn.createStatement()) {
			try(ResultSet rs = stm.executeQuery(NAMESPACES_ENTRIES_DML)) {
				while(rs.next()) {
					Curie entry = new Curie(rs.getString(1),rs.getString(2),rs.getString(3),rs.getString(4));
					
					retval.put(entry.id,entry);
					retval.put(entry.namespace,entry);
				}
			}
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			// We cannot throw it because the interface does not allow it
			// throw outer;
		}
		
		return retval.entrySet();
	}
	
	public boolean equals(Object o) {
		if(o instanceof CurieCache) {
			return dbfile.equals(((CurieCache)o).dbfile);
		}
		
		return false;
	}
	
	public Curie get(Object key) {
		if(key instanceof String) {
			try(PreparedStatement pstm = conn.prepareStatement(NAMESPACES_GET_DML)) {
				String keyS = (String)key;
				pstm.setString(1,keyS);
				pstm.setString(2,keyS);
				
				try(ResultSet rs = pstm.executeQuery()) {
					if(rs.next()) {
						return new Curie(rs.getString(1),rs.getString(2),rs.getString(3),rs.getString(4));
					} else {
						return null;
					}
				}
			} catch(SQLException outer) {
				try {
					conn.rollback();
				} catch(SQLException inner) {
					outer.setNextException(inner);
				}
				
				// We cannot throw it because the interface does not allow it
				// throw outer;
			}
		}
		
		return null;
	}
	
	/* This should be implemented from Object
	public int hashCode() {
	}
	*/
	
	public boolean isEmpty() {
		// The instance should only be useable when it is properly populated
		return size()==0;
	}
	
	public Set<String> keySet() {
		HashSet<String> retval = new HashSet<>();
		
		try(Statement stm = conn.createStatement()) {
			try(ResultSet rs = stm.executeQuery(NAMESPACES_ENTRIES_DML)) {
				while(rs.next()) {
					retval.add(rs.getString(1));
					retval.add(rs.getString(2));
				}
			}
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			// We cannot throw it because the interface does not allow it
			// throw outer;
		}
		
		return retval;
	}
	
	public Curie put(String key, Curie value) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	public void putAll(Map<? extends String,? extends Curie> m) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	public Curie remove(Object key) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	public int size() {
		try(Statement stm = conn.createStatement()) {
			try(ResultSet rs = stm.executeQuery(NAMESPACES_COUNT_DML)) {
				if(rs.next()) {
					return rs.getInt(1);
				}
			}
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			// We cannot throw it because the interface does not allow it
			// throw outer;
		}
		
		return 0;
	}
	
	public Collection<Curie> values() {
		ArrayList<Curie> retval = new ArrayList<>();
		
		try(Statement stm = conn.createStatement()) {
			try(ResultSet rs = stm.executeQuery(NAMESPACES_ENTRIES_DML)) {
				while(rs.next()) {
					Curie entry = new Curie(rs.getString(1),rs.getString(2),rs.getString(3),rs.getString(4));
					retval.add(entry);
				}
			}
		} catch(SQLException outer) {
			try {
				conn.rollback();
			} catch(SQLException inner) {
				outer.setNextException(inner);
			}
			
			// We cannot throw it because the interface does not allow it
			// throw outer;
		}
		
		return retval;
	}
	
	// Default methods being reimplemented to fail fast
	@Override
	public Curie merge(String key,Curie value, BiFunction<? super Curie,? super Curie,? extends Curie> remappingFunction) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	@Override
	public Curie putIfAbsent(String key,Curie value) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	@Override
	public boolean remove(Object key, Object value) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	@Override
	public Curie replace(String key, Curie value) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	@Override
	public boolean replace(String key, Curie oldValue, Curie newValue) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	@Override
	public void replaceAll(BiFunction<? super String,? super Curie,? extends Curie> function) {
		throw new UnsupportedOperationException("Read only Curie cache");
	}
	
	public final static void main(String args[])
	{
		try {
			CurieCache cc = new CurieCache("/tmp/prueba.sqlite3");
			Curie uni = cc.get("uniprot");
			System.out.println(uni!=null ? uni.toString() : "(null)");
			System.out.println(cc.containsKey("pubmed"));
			Curie mir = cc.get("MIR:00000005");
			System.out.println(mir!=null ? mir.toString() : "(null)");
			Curie con = cc.get("conejo");
			System.out.println(con!=null ? con.toString() : "(null)");
			System.exit(0);
		} catch(Exception e) {
			e.printStackTrace();
			System.exit(1);
		}
		
	}
}
